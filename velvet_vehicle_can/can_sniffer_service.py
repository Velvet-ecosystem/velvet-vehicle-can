from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Iterable, List, Optional, Tuple
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)

from .can_fingerprint import CanFingerprint, CanFingerprintBuilder
from .vehicle_profile import VehicleProfile, VehicleProfileStore
from .can_dialect_learner import CanDialectLearner, LabeledEvent, TelemetrySample, CanFrame
from .qualification_gate import (
    QualificationGate,
    QualificationResult,
    DriverState,
    HealthState,
    CapabilityStage,
)

# A minimal CAN interface contract (swap in python-can, socketcan, etc.)
CanReadFn = Callable[[], Optional[Tuple[float, int, bytes]]]
# returns (ts, can_id, data) or None if no frame available


@dataclass
class SnifferConfig:
    bus_name: str = "obd_can"
    profile_store_dir: str = "data/vehicle_profiles"
    fingerprint_window_s: float = 30.0
    frame_buffer_max: int = 50_000
    fingerprint_refresh_s: float = 5.0
    qualification_refresh_s: float = 0.25

    # learning
    learning_enabled: bool = True
    retain_raw_logs: bool = False  # if False, keep only rolling buffer
    default_new_profile_stage: int = 0

    # thresholds (conservative defaults)
    profile_match_required: bool = True  # require fingerprint match to load profile for control


@dataclass
class VehicleRuntimeState:
    fingerprint: Optional[CanFingerprint] = None
    profile: Optional[VehicleProfile] = None
    qualification: Optional[QualificationResult] = None
    health: HealthState = field(default_factory=HealthState)
    last_fingerprint_ts: float = 0.0
    last_qualification_ts: float = 0.0
    matched_profile_digest: Optional[str] = None


class CanSnifferService:
    """
    Read-only CAN sniffer + profile manager.

    Responsibilities:
    - Collect frames
    - Build/refresh fingerprint
    - Load/create VehicleProfile
    - Provide HealthState + QualificationResult
    - Feed learner (optional) with labeled events & telemetry (supplied externally)

    Not responsible for:
    - CAN injection / actuation
    - UI prompts
    """

    def __init__(
        self,
        read_frame: CanReadFn,
        config: Optional[SnifferConfig] = None,
        gate: Optional[QualificationGate] = None,
        learner: Optional[CanDialectLearner] = None,
        store: Optional[VehicleProfileStore] = None,
    ) -> None:
        self.read_frame = read_frame
        self.cfg = config or SnifferConfig()
        self.gate = gate or QualificationGate()
        self.learner = learner or CanDialectLearner()
        self.store = store or VehicleProfileStore(self.cfg.profile_store_dir)

        self.fp_builder = CanFingerprintBuilder(bus_name=self.cfg.bus_name)
        self.frames: Deque[CanFrame] = deque(maxlen=self.cfg.frame_buffer_max)
        self.state = VehicleRuntimeState()

        # external inputs (set by other subsystems)
        self._driver_state = DriverState()
        self._telemetry: Deque[TelemetrySample] = deque(maxlen=20_000)
        self._labeled_events: Deque[LabeledEvent] = deque(maxlen=2_000)

    # ---------- Public setters (inputs from other modules) ----------

    def set_driver_state(self, driver_state: DriverState) -> None:
        self._driver_state = driver_state

    def push_telemetry(self, sample: TelemetrySample) -> None:
        self._telemetry.append(sample)

    def push_labeled_event(self, event: LabeledEvent) -> None:
        self._labeled_events.append(event)

    # ---------- Main loop tick ----------

    def tick(self) -> VehicleRuntimeState:
        """
        Call frequently (e.g., 50-200 Hz). Pulls frames (if available) and updates
        fingerprint + qualification on their own cadences.
        """
        self._drain_frames()

        now = time.time()

        # Refresh fingerprint periodically
        if (now - self.state.last_fingerprint_ts) >= self.cfg.fingerprint_refresh_s:
            self._refresh_fingerprint()
            self.state.last_fingerprint_ts = now

        # Refresh qualification periodically
        if (now - self.state.last_qualification_ts) >= self.cfg.qualification_refresh_s:
            self._refresh_health()
            self._refresh_qualification()
            self.state.last_qualification_ts = now

        return self.state

    # ---------- Internals ----------

    def _drain_frames(self, max_pull: int = 500) -> None:
        for _ in range(max_pull):
            f = self.read_frame()
            if f is None:
                break
            self.frames.append(f)

    def _refresh_fingerprint(self) -> None:
        # NOTE: VIN fetching via OBD is intentionally not done here.
        # A separate OBD service can provide VIN to pass in.
        fp = self.fp_builder.build(self.frames, vin=None, window_seconds=self.cfg.fingerprint_window_s)
        self.state.fingerprint = fp

        digest = fp.digest()
        self.state.matched_profile_digest = digest

        # Load or create profile bound to this digest
        profile = self.store.load(digest)
        if profile is None:
            profile = VehicleProfile(
                fingerprint_digest=digest,
                vin_hash=fp.vin_hash,
                stage=self.cfg.default_new_profile_stage,
                notes=f"auto-created for {self.cfg.bus_name}",
            )
            self.store.save(profile)
            logger.info(f"[vehicle] created new VehicleProfile {digest}")

        self.state.profile = profile

    def _refresh_health(self) -> None:
        """
        Populate HealthState. This starts minimal; other subsystems can enrich it.
        """
        h = HealthState()

        # Fingerprint match: if profile exists, we consider it matched by digest binding.
        # If later you add multi-bus or VIN checks, enforce them here.
        h.fingerprint_match = self.state.profile is not None and self.state.fingerprint is not None

        # Placeholder integrity checks; actual checksum/counter validation belongs in CAN parsing layer.
        h.checksum_ok = True
        h.counter_ok = True

        # Placeholder sensor fusion; update from telemetry consistency logic later.
        h.sensor_agreement_ok = True

        # Bus load: if we are dropping frames or buffer overrun, flag.
        h.bus_load_ok = True

        h.faulted = False
        h.fault_reason = ""

        self.state.health = h

    def _refresh_qualification(self) -> None:
        q = self.gate.evaluate(
            profile=self.state.profile,
            driver=self._driver_state,
            health=self.state.health,
        )
        self.state.qualification = q

    # ---------- Learning hooks ----------

    def run_learning_pass(self, lookback_s: float = 15.0) -> Optional[VehicleProfile]:
        """
        Run a conservative learning pass over recent frames using labeled events.
        This does NOT change the profile stage automatically; it only updates
        candidate SignalMap definitions and confidence. Validation should happen elsewhere.
        """
        if not self.cfg.learning_enabled:
            return None

        profile = self.state.profile
        if profile is None:
            return None

        now = time.time()
        start = now - lookback_s

        frames = [f for f in self.frames if f[0] >= start]
        events = [e for e in self._labeled_events if e.end_ts >= start]
        telemetry = [t for t in self._telemetry if t.ts >= start]

        if not frames or not events:
            return profile

        learned_map = self.learner.learn_signal_map(frames, events, telemetry=telemetry or None)

        # Merge: only fill missing signals or increase confidence if improved
        self._merge_signal_map(profile, learned_map)
        self.store.save(profile)
        self.state.profile = profile
        return profile

    def _merge_signal_map(self, profile: VehicleProfile, learned) -> None:
        """
        Conservative merge: if a target signal is empty, accept learned.
        If present, only replace if confidence increases meaningfully.
        """
        dst = profile.signal_map
        src = learned

        def take(dst_sig, src_sig):
            if src_sig is None:
                return dst_sig
            if dst_sig is None:
                return src_sig
            if float(src_sig.confidence or 0.0) > float(dst_sig.confidence or 0.0) + 0.05:
                return src_sig
            return dst_sig

        dst.wheel_speed = take(dst.wheel_speed, src.wheel_speed)
        dst.steering_angle = take(dst.steering_angle, src.steering_angle)
        dst.steering_request = take(dst.steering_request, src.steering_request)
        dst.brake_request = take(dst.brake_request, src.brake_request)
        dst.throttle_request = take(dst.throttle_request, src.throttle_request)
        dst.gear = take(dst.gear, src.gear)
        dst.cruise_state = take(dst.cruise_state, src.cruise_state)

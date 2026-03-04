from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Dict, Tuple
import time

from .vehicle_profile import VehicleProfile


class CapabilityStage(IntEnum):
    """
    Mirrors docs/can_learning_pipeline.md stages.
    Keep these stable; they become part of stored profile semantics.
    """
    PASSIVE_SNIFF = 0
    STATUS_DECODE = 1
    SHADOW_PREDICTION = 2
    LIMITED_INJECTION = 3
    EXTENDED_INJECTION = 4


@dataclass
class DriverState:
    """
    Inputs from higher layers (driver monitoring, seat presence, etc).
    Keep it minimal and explicit.
    """
    driver_present: bool = True
    attentive: bool = True
    manual_override: bool = False  # e.g. steering torque/brake press detected
    explicitly_armed: bool = False  # explicit consent UI action
    last_override_ts: float = 0.0


@dataclass
class HealthState:
    """
    Inputs from CAN integrity checks and sensor fusion.
    """
    fingerprint_match: bool = True
    checksum_ok: bool = True
    counter_ok: bool = True
    sensor_agreement_ok: bool = True
    bus_load_ok: bool = True
    faulted: bool = False
    fault_reason: str = ""


@dataclass
class AuthorityEnvelope:
    """
    Limits on how much control is permitted.
    Interpreted by whichever module performs injection.
    Units are intentionally generic; calibrate per platform.
    """
    max_steer: float = 0.0       # e.g. torque request limit or angle delta limit
    max_accel: float = 0.0       # throttle/accel request limit
    max_decel: float = 0.0       # brake/decel request limit
    rate_limit_hz: float = 0.0   # how often to send control frames
    notes: str = ""


@dataclass
class QualificationResult:
    allowed_stage: CapabilityStage
    envelope: AuthorityEnvelope
    reason: str
    timestamp: float = field(default_factory=lambda: time.time())


class QualificationGate:
    """
    The safety-centric decision layer for capability staging.

    This DOES NOT inject.
    It only decides whether injection is allowed and under what envelope.

    Hard rule:
    - Any fault or manual override collapses to PASSIVE_SNIFF immediately.
    """

    def __init__(
        self,
        cooldown_after_override_s: float = 5.0,
        min_validation_for_limited: float = 0.85,
        min_validation_for_extended: float = 0.93,
        min_confidence_for_limited: float = 0.75,
        min_confidence_for_extended: float = 0.88,
    ) -> None:
        self.cooldown_after_override_s = cooldown_after_override_s
        self.min_validation_for_limited = min_validation_for_limited
        self.min_validation_for_extended = min_validation_for_extended
        self.min_confidence_for_limited = min_confidence_for_limited
        self.min_confidence_for_extended = min_confidence_for_extended

    def evaluate(
        self,
        profile: Optional[VehicleProfile],
        driver: DriverState,
        health: HealthState,
    ) -> QualificationResult:
        now = time.time()

        # 0) No profile? No trust.
        if profile is None:
            return QualificationResult(
                allowed_stage=CapabilityStage.PASSIVE_SNIFF,
                envelope=AuthorityEnvelope(notes="no_profile"),
                reason="No vehicle profile loaded; read-only mode.",
            )

        # 1) Any fault? Drop to passive sniff.
        if health.faulted or not self._health_ok(health):
            reason = health.fault_reason or "Health checks failed; read-only mode."
            return QualificationResult(
                allowed_stage=CapabilityStage.PASSIVE_SNIFF,
                envelope=AuthorityEnvelope(notes="health_failed"),
                reason=reason,
            )

        # 2) Driver not present or not attentive? Drop to status decode at most.
        if not driver.driver_present:
            return QualificationResult(
                allowed_stage=CapabilityStage.PASSIVE_SNIFF,
                envelope=AuthorityEnvelope(notes="driver_absent"),
                reason="Driver not present; read-only mode.",
            )

        if not driver.attentive:
            return QualificationResult(
                allowed_stage=CapabilityStage.STATUS_DECODE,
                envelope=self._envelope_for_status_only(),
                reason="Driver not attentive; decode-only mode.",
            )

        # 3) Manual override? Immediate drop + cooldown.
        if driver.manual_override:
            return QualificationResult(
                allowed_stage=CapabilityStage.PASSIVE_SNIFF,
                envelope=AuthorityEnvelope(notes="manual_override"),
                reason="Manual override detected; dropping to read-only.",
            )

        if driver.last_override_ts and (now - driver.last_override_ts) < self.cooldown_after_override_s:
            return QualificationResult(
                allowed_stage=CapabilityStage.STATUS_DECODE,
                envelope=self._envelope_for_status_only(),
                reason="Cooldown after override; decode-only mode.",
            )

        # 4) Compute signal confidence (minimum required signals)
        conf = self._minimum_control_confidence(profile)
        val = float(profile.validation_score or 0.0)

        # 5) Shadow prediction is allowed when basic decode exists
        # Use stored profile.stage as an upper bound (what we’ve validated historically).
        stage_cap = CapabilityStage(min(int(profile.stage), int(CapabilityStage.EXTENDED_INJECTION)))

        # Always at least status decode if healthy and driver present/attentive
        allowed = CapabilityStage.STATUS_DECODE

        # Allow shadow prediction when we have enough mapping to make predictions.
        if stage_cap >= CapabilityStage.SHADOW_PREDICTION:
            allowed = CapabilityStage.SHADOW_PREDICTION

        # Limited injection requires explicit arming + confidence + validation.
        if (
            stage_cap >= CapabilityStage.LIMITED_INJECTION
            and driver.explicitly_armed
            and conf >= self.min_confidence_for_limited
            and val >= self.min_validation_for_limited
        ):
            allowed = CapabilityStage.LIMITED_INJECTION

        # Extended injection is stricter.
        if (
            stage_cap >= CapabilityStage.EXTENDED_INJECTION
            and driver.explicitly_armed
            and conf >= self.min_confidence_for_extended
            and val >= self.min_validation_for_extended
        ):
            allowed = CapabilityStage.EXTENDED_INJECTION

        # 6) Envelope selection per allowed stage
        env = self._envelope_for_stage(allowed)

        return QualificationResult(
            allowed_stage=allowed,
            envelope=env,
            reason=f"stage={allowed.name} conf={conf:.2f} val={val:.2f} armed={driver.explicitly_armed}",
        )

    def _health_ok(self, health: HealthState) -> bool:
        return all([
            health.fingerprint_match,
            health.checksum_ok,
            health.counter_ok,
            health.sensor_agreement_ok,
            health.bus_load_ok,
        ])

    def _minimum_control_confidence(self, profile: VehicleProfile) -> float:
        """
        Conservative: compute minimum confidence among required control signals.
        If a signal is missing, confidence is 0.
        """
        sm = profile.signal_map
        required = [
            sm.steering_request,
            sm.brake_request,
            sm.throttle_request,
        ]
        confidences = []
        for sig in required:
            if sig is None:
                confidences.append(0.0)
            else:
                confidences.append(float(sig.confidence or 0.0))
        return min(confidences) if confidences else 0.0

    def _envelope_for_status_only(self) -> AuthorityEnvelope:
        return AuthorityEnvelope(
            max_steer=0.0,
            max_accel=0.0,
            max_decel=0.0,
            rate_limit_hz=0.0,
            notes="decode_only",
        )

    def _envelope_for_stage(self, stage: CapabilityStage) -> AuthorityEnvelope:
        if stage <= CapabilityStage.SHADOW_PREDICTION:
            return self._envelope_for_status_only()

        if stage == CapabilityStage.LIMITED_INJECTION:
            return AuthorityEnvelope(
                max_steer=0.15,
                max_accel=0.10,
                max_decel=0.12,
                rate_limit_hz=20.0,
                notes="limited_injection",
            )

        if stage == CapabilityStage.EXTENDED_INJECTION:
            return AuthorityEnvelope(
                max_steer=0.35,
                max_accel=0.25,
                max_decel=0.30,
                rate_limit_hz=50.0,
                notes="extended_injection",
            )

        return self._envelope_for_status_only()

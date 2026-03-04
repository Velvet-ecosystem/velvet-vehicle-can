from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
import json
import time
from pathlib import Path

from .can_fingerprint import CanFingerprint


@dataclass
class IntegrityRule:
    """Describes message integrity (counter/checksum) needed to inject safely."""
    counter: Optional[Dict] = None   # e.g. {"start_bit": 8, "length": 4, "mod": 16}
    checksum: Optional[Dict] = None  # e.g. {"type": "crc8", "poly": 0x2F, "byte_index": 7}


@dataclass
class SignalDef:
    """
    A learned mapping from CAN frame bytes to a physical signal.
    """
    can_id: int
    start: int
    length: int
    endian: str = "little"   # "little" | "big"
    signed: bool = False
    scale: float = 1.0
    offset: float = 0.0
    integrity: IntegrityRule = field(default_factory=IntegrityRule)
    confidence: float = 0.0  # 0..1


@dataclass
class SignalMap:
    """
    Core signals Velvet cares about. Expand as needed.
    """
    wheel_speed: Optional[SignalDef] = None
    steering_angle: Optional[SignalDef] = None
    steering_request: Optional[SignalDef] = None
    brake_request: Optional[SignalDef] = None
    throttle_request: Optional[SignalDef] = None

    # Optional extras
    gear: Optional[SignalDef] = None
    cruise_state: Optional[SignalDef] = None


@dataclass
class VehicleProfile:
    """
    Local-first learned profile for one vehicle identity.
    """
    fingerprint_digest: str
    vin_hash: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    signal_map: SignalMap = field(default_factory=SignalMap)

    # Capability gating
    stage: int = 0  # 0..6 pipeline stage
    notes: str = ""
    validation_score: float = 0.0

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_json(self) -> str:
        def _convert(obj):
            if hasattr(obj, "__dict__"):
                return asdict(obj)
            return obj
        return json.dumps(asdict(self), indent=2, default=_convert)


class VehicleProfileStore:
    """
    Very simple JSON store. Swap later for MemoryCore-backed storage if desired.
    """
    def __init__(self, root_dir: str = "data/vehicle_profiles") -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, fingerprint_digest: str) -> Path:
        return self.root / f"{fingerprint_digest}.json"

    def save(self, profile: VehicleProfile) -> None:
        profile.touch()
        p = self._path(profile.fingerprint_digest)
        p.write_text(profile.to_json(), encoding="utf-8")

    def load(self, fingerprint_digest: str) -> Optional[VehicleProfile]:
        p = self._path(fingerprint_digest)
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        return self._from_dict(raw)

    def _from_dict(self, d: Dict) -> VehicleProfile:
        # Minimal safe reconstruction (keep it simple; expand as you add fields)
        sm = d.get("signal_map", {}) or {}
        signal_map = SignalMap(
            wheel_speed=_sig(sm.get("wheel_speed")),
            steering_angle=_sig(sm.get("steering_angle")),
            steering_request=_sig(sm.get("steering_request")),
            brake_request=_sig(sm.get("brake_request")),
            throttle_request=_sig(sm.get("throttle_request")),
            gear=_sig(sm.get("gear")),
            cruise_state=_sig(sm.get("cruise_state")),
        )
        vp = VehicleProfile(
            fingerprint_digest=d["fingerprint_digest"],
            vin_hash=d.get("vin_hash"),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            signal_map=signal_map,
            stage=int(d.get("stage", 0)),
            notes=d.get("notes", ""),
            validation_score=float(d.get("validation_score", 0.0)),
        )
        return vp


def _sig(sd: Optional[Dict]) -> Optional[SignalDef]:
    if not sd:
        return None
    integ = sd.get("integrity", {}) or {}
    rule = IntegrityRule(counter=integ.get("counter"), checksum=integ.get("checksum"))
    return SignalDef(
        can_id=int(sd["can_id"]),
        start=int(sd["start"]),
        length=int(sd["length"]),
        endian=sd.get("endian", "little"),
        signed=bool(sd.get("signed", False)),
        scale=float(sd.get("scale", 1.0)),
        offset=float(sd.get("offset", 0.0)),
        integrity=rule,
        confidence=float(sd.get("confidence", 0.0)),
    )

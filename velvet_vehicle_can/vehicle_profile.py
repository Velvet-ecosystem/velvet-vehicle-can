from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .evidence_topology import VehicleEvidenceTopology


@dataclass
class IntegrityRule:
    """Message integrity information retained for review and qualification."""

    counter: Optional[Dict] = None
    checksum: Optional[Dict] = None


@dataclass
class SignalDef:
    """A learned mapping from CAN frame bytes to a physical signal."""

    can_id: int
    start: int
    length: int
    endian: str = "little"
    signed: bool = False
    scale: float = 1.0
    offset: float = 0.0
    integrity: IntegrityRule = field(default_factory=IntegrityRule)
    confidence: float = 0.0


@dataclass
class SignalMap:
    """Canonical observations currently mapped for one vehicle profile."""

    wheel_speed: Optional[SignalDef] = None
    steering_angle: Optional[SignalDef] = None
    steering_request: Optional[SignalDef] = None
    brake_request: Optional[SignalDef] = None
    throttle_request: Optional[SignalDef] = None
    engine_rpm: Optional[SignalDef] = None
    engine_running: Optional[SignalDef] = None
    supply_voltage: Optional[SignalDef] = None
    gear: Optional[SignalDef] = None
    ignition_state: Optional[SignalDef] = None
    driver_door: Optional[SignalDef] = None
    o2_fault: Optional[SignalDef] = None
    cruise_state: Optional[SignalDef] = None


@dataclass
class VehicleProfile:
    """Local-first learned profile for one vehicle identity.

    ``signal_map`` describes CAN decoding candidates. ``evidence_topology``
    describes every known source for those same canonical body facts, including
    hard-wired and specialized retrofit paths that may exist outside CAN.
    Neither structure grants authority.
    """

    fingerprint_digest: str
    vin_hash: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    signal_map: SignalMap = field(default_factory=SignalMap)
    evidence_topology: VehicleEvidenceTopology = field(
        default_factory=VehicleEvidenceTopology
    )
    stage: int = 0
    notes: str = ""
    validation_score: float = 0.0

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        signal_map = {}
        for item in fields(self.signal_map):
            definition = getattr(self.signal_map, item.name)
            signal_map[item.name] = asdict(definition) if definition is not None else None
        return {
            "schema": "velvet.vehicle_profile.v2",
            "fingerprint_digest": self.fingerprint_digest,
            "vin_hash": self.vin_hash,
            "created_at": float(self.created_at),
            "updated_at": float(self.updated_at),
            "signal_map": signal_map,
            "evidence_topology": self.evidence_topology.to_dict(),
            "stage": int(self.stage),
            "notes": self.notes,
            "validation_score": float(self.validation_score),
            "read_only_observation_profile": True,
            "grants_authority": False,
            "actuation_granted": False,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class VehicleProfileStore:
    """Simple local JSON profile store with backward-compatible loading."""

    def __init__(self, root_dir: str = "data/vehicle_profiles") -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, fingerprint_digest: str) -> Path:
        return self.root / ("%s.json" % fingerprint_digest)

    def save(self, profile: VehicleProfile) -> None:
        if not isinstance(profile, VehicleProfile):
            raise TypeError("profile must be a VehicleProfile")
        profile.touch()
        path = self._path(profile.fingerprint_digest)
        path.write_text(profile.to_json() + "\n", encoding="utf-8")

    def load(self, fingerprint_digest: str) -> Optional[VehicleProfile]:
        path = self._path(fingerprint_digest)
        if not path.exists():
            return None
        return self.load_path(path)

    def load_path(self, path: Path) -> VehicleProfile:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("vehicle profile root must be an object")
        return self._from_dict(dict(raw))

    def _from_dict(self, value: Dict[str, Any]) -> VehicleProfile:
        signal_map_value = value.get("signal_map", {}) or {}
        if not isinstance(signal_map_value, Mapping):
            raise ValueError("signal_map must be an object")
        signal_map = SignalMap(
            wheel_speed=_sig(signal_map_value.get("wheel_speed")),
            steering_angle=_sig(signal_map_value.get("steering_angle")),
            steering_request=_sig(signal_map_value.get("steering_request")),
            brake_request=_sig(signal_map_value.get("brake_request")),
            throttle_request=_sig(signal_map_value.get("throttle_request")),
            engine_rpm=_sig(signal_map_value.get("engine_rpm")),
            engine_running=_sig(signal_map_value.get("engine_running")),
            supply_voltage=_sig(signal_map_value.get("supply_voltage")),
            gear=_sig(signal_map_value.get("gear")),
            ignition_state=_sig(signal_map_value.get("ignition_state")),
            driver_door=_sig(signal_map_value.get("driver_door")),
            o2_fault=_sig(signal_map_value.get("o2_fault")),
            cruise_state=_sig(signal_map_value.get("cruise_state")),
        )
        return VehicleProfile(
            fingerprint_digest=str(value["fingerprint_digest"]),
            vin_hash=value.get("vin_hash"),
            created_at=float(value.get("created_at", time.time())),
            updated_at=float(value.get("updated_at", time.time())),
            signal_map=signal_map,
            evidence_topology=VehicleEvidenceTopology.from_dict(
                value.get("evidence_topology")
            ),
            stage=int(value.get("stage", 0)),
            notes=str(value.get("notes", "")),
            validation_score=float(value.get("validation_score", 0.0)),
        )


def _sig(value: Optional[Mapping[str, Any]]) -> Optional[SignalDef]:
    if not value:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("signal definition must be an object")
    integrity = value.get("integrity", {}) or {}
    if not isinstance(integrity, Mapping):
        raise ValueError("signal integrity must be an object")
    return SignalDef(
        can_id=int(value["can_id"]),
        start=int(value["start"]),
        length=int(value["length"]),
        endian=str(value.get("endian", "little")),
        signed=bool(value.get("signed", False)),
        scale=float(value.get("scale", 1.0)),
        offset=float(value.get("offset", 0.0)),
        integrity=IntegrityRule(
            counter=integrity.get("counter"),
            checksum=integrity.get("checksum"),
        ),
        confidence=float(value.get("confidence", 0.0)),
    )

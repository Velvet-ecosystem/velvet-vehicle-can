# SPDX-License-Identifier: GPL-3.0-only
"""Capability-aware observations decoded from one vehicle CAN profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Tuple

from .can_observer import ObservedCanFrame
from .evidence_topology import (
    EvidenceSourceKind,
    EvidenceSourceState,
    SignalSourceBinding,
)
from .signal_decoder import decode_signal_map
from .signal_registry import get_signal_by_profile_field
from .vehicle_profile import VehicleProfile


@dataclass(frozen=True)
class ProfileObservation:
    canonical_signal: str
    profile_field: str
    value: float
    raw_value: int
    unit: Optional[str]
    confidence: float
    can_id: int
    timestamp: float
    source_ref: str
    source_kind: EvidenceSourceKind
    source_state: EvidenceSourceState
    topology_declared: bool
    independent_cross_check_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_signal": self.canonical_signal,
            "profile_field": self.profile_field,
            "value": self.value,
            "raw_value": self.raw_value,
            "unit": self.unit,
            "confidence": self.confidence,
            "can_id": self.can_id,
            "can_id_hex": "0x%x" % self.can_id,
            "timestamp": self.timestamp,
            "source_ref": self.source_ref,
            "source_kind": self.source_kind.value,
            "source_state": self.source_state.value,
            "topology_declared": self.topology_declared,
            "independent_cross_check_available": self.independent_cross_check_available,
            "status": "observation-only",
            "read_only": True,
            "authority": "none",
            "grants_authority": False,
            "actuation_granted": False,
            "actuation_performed": False,
        }


def decode_profile_observations(
    frames: Iterable[ObservedCanFrame],
    profile: VehicleProfile,
    *,
    bus_source_ref: str = "can:obd_can",
    minimum_confidence: float = 0.0,
    max_signals: int = 32,
) -> Tuple[ProfileObservation, ...]:
    """Decode CAN values while preserving the profile's source topology.

    A decoded CAN value proves only that a configured mapping produced a value.
    It does not prove that the mapping is semantically correct.  When a topology
    binding is absent, the output is labeled as an implicit detected CAN source
    rather than silently marking the source verified.
    """

    if not isinstance(profile, VehicleProfile):
        raise TypeError("profile must be a VehicleProfile")
    if not isinstance(bus_source_ref, str) or not bus_source_ref.strip():
        raise ValueError("bus_source_ref must be non-empty text")

    decoded = decode_signal_map(
        frames,
        profile.signal_map,
        minimum_confidence=minimum_confidence,
        max_signals=max_signals,
    )
    observations = []
    for item in decoded:
        catalog = get_signal_by_profile_field(item.name)
        if catalog is None:
            continue
        binding = _can_binding(profile, catalog.canonical_name)
        if binding is None:
            source_ref = bus_source_ref.strip()
            source_kind = EvidenceSourceKind.CAN
            source_state = EvidenceSourceState.DETECTED
            confidence = item.confidence
            topology_declared = False
        else:
            source_ref = binding.source_ref
            source_kind = binding.source_kind
            source_state = binding.state
            confidence = min(item.confidence, float(binding.confidence_cap))
            topology_declared = True

        observations.append(
            ProfileObservation(
                canonical_signal=catalog.canonical_name,
                profile_field=item.name,
                value=item.value,
                raw_value=item.raw_value,
                unit=catalog.unit,
                confidence=confidence,
                can_id=item.can_id,
                timestamp=item.timestamp,
                source_ref=source_ref,
                source_kind=source_kind,
                source_state=source_state,
                topology_declared=topology_declared,
                independent_cross_check_available=profile.evidence_topology.has_independent_cross_check(
                    catalog.canonical_name
                ),
            )
        )
    return tuple(observations)


def summarize_profile_observations(
    observations: Iterable[ProfileObservation],
    profile: VehicleProfile,
) -> Mapping[str, Any]:
    if not isinstance(profile, VehicleProfile):
        raise TypeError("profile must be a VehicleProfile")
    items = [item.to_dict() for item in observations]
    return {
        "schema": "velvet.vehicle.profile_observations.v1",
        "fingerprint_digest": profile.fingerprint_digest,
        "vehicle_generation": profile.evidence_topology.generation.value,
        "observation_count": len(items),
        "observations": items,
        "evidence_topology": profile.evidence_topology.to_dict(),
        "status": "observation-only",
        "read_only": True,
        "authority": "none",
        "grants_authority": False,
        "actuation_granted": False,
        "actuation_performed": False,
    }


def _can_binding(
    profile: VehicleProfile,
    canonical_signal: str,
) -> Optional[SignalSourceBinding]:
    matches = [
        item
        for item in profile.evidence_topology.sources_for(canonical_signal)
        if item.source_kind
        in {EvidenceSourceKind.CAN, EvidenceSourceKind.OBD_DIAGNOSTIC}
    ]
    return matches[0] if matches else None

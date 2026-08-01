# SPDX-License-Identifier: GPL-3.0-only
"""Source-aware vehicle evidence topology for modern and legacy bodies.

A vehicle may expose the same body fact through CAN, a diagnostic transport,
a dedicated hard-wired input, or a specialized retrofit sensor.  This module
records those paths without turning availability, confidence, or agreement into
a permission grant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Tuple

from .signal_registry import CANONICAL_SIGNAL_CATALOG, get_signal_by_name


_SOURCE_REF_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")


class VehicleGeneration(str, Enum):
    UNKNOWN = "unknown"
    LEGACY = "legacy"
    MIXED = "mixed"
    MODERN = "modern"


class EvidenceSourceKind(str, Enum):
    CAN = "can"
    OBD_DIAGNOSTIC = "obd_diagnostic"
    HARDWIRED = "hardwired"
    SPECIALIZED = "specialized"


class EvidenceSourceState(str, Enum):
    DECLARED = "declared"
    DETECTED = "detected"
    VERIFIED = "verified"


_STATE_RANK = {
    EvidenceSourceState.DECLARED: 0,
    EvidenceSourceState.DETECTED: 1,
    EvidenceSourceState.VERIFIED: 2,
}


@dataclass(frozen=True)
class SignalSourceBinding:
    """One read-only path capable of supplying a canonical vehicle signal."""

    canonical_signal: str
    source_kind: EvidenceSourceKind
    source_ref: str
    transport: str
    state: EvidenceSourceState = EvidenceSourceState.DECLARED
    priority: int = 100
    confidence_cap: float = 1.0
    independent: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        try:
            source_kind = EvidenceSourceKind(self.source_kind)
            state = EvidenceSourceState(self.state)
        except ValueError as exc:
            raise ValueError("unsupported evidence source kind or state") from exc
        object.__setattr__(self, "source_kind", source_kind)
        object.__setattr__(self, "state", state)

        if get_signal_by_name(self.canonical_signal) is None:
            raise KeyError("unregistered canonical vehicle signal: %s" % self.canonical_signal)
        if not isinstance(self.source_ref, str) or not _SOURCE_REF_PATTERN.fullmatch(
            self.source_ref
        ):
            raise ValueError("source_ref must be a normalized local identifier")
        if not isinstance(self.transport, str) or not self.transport.strip():
            raise ValueError("transport must be non-empty text")
        if self.transport != self.transport.strip():
            raise ValueError("transport must be normalized")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer")
        if not 0 <= self.priority <= 1000:
            raise ValueError("priority must be between 0 and 1000")
        if isinstance(self.confidence_cap, bool) or not isinstance(
            self.confidence_cap, (int, float)
        ):
            raise TypeError("confidence_cap must be numeric")
        if not 0.0 <= float(self.confidence_cap) <= 1.0:
            raise ValueError("confidence_cap must be between 0 and 1")
        if not isinstance(self.independent, bool):
            raise TypeError("independent must be boolean")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_signal": self.canonical_signal,
            "source_kind": self.source_kind.value,
            "source_ref": self.source_ref,
            "transport": self.transport,
            "state": self.state.value,
            "priority": self.priority,
            "confidence_cap": float(self.confidence_cap),
            "independent": self.independent,
            "notes": self.notes,
            "read_only": True,
            "authority": "none",
            "grants_permission": False,
            "grants_authority": False,
            "actuation_granted": False,
            "actuation_performed": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SignalSourceBinding":
        if not isinstance(value, Mapping):
            raise TypeError("signal source binding must be a mapping")
        return cls(
            canonical_signal=str(value.get("canonical_signal", "")),
            source_kind=EvidenceSourceKind(str(value.get("source_kind", ""))),
            source_ref=str(value.get("source_ref", "")),
            transport=str(value.get("transport", "")),
            state=EvidenceSourceState(str(value.get("state", "declared"))),
            priority=int(value.get("priority", 100)),
            confidence_cap=float(value.get("confidence_cap", 1.0)),
            independent=value.get("independent", True) is True,
            notes=str(value.get("notes", "")),
        )


@dataclass(frozen=True)
class VehicleEvidenceTopology:
    """All declared observation paths for one vehicle body."""

    generation: VehicleGeneration = VehicleGeneration.UNKNOWN
    bindings: Tuple[SignalSourceBinding, ...] = ()

    def __post_init__(self) -> None:
        try:
            generation = VehicleGeneration(self.generation)
        except ValueError as exc:
            raise ValueError("unsupported vehicle generation") from exc
        object.__setattr__(self, "generation", generation)
        bindings = tuple(self.bindings)
        object.__setattr__(self, "bindings", bindings)

        seen = set()
        for binding in bindings:
            if not isinstance(binding, SignalSourceBinding):
                raise TypeError("bindings must contain SignalSourceBinding values")
            key = (binding.canonical_signal, binding.source_ref)
            if key in seen:
                raise ValueError(
                    "duplicate evidence source binding: %s via %s" % key
                )
            seen.add(key)

    def sources_for(self, canonical_signal: str) -> Tuple[SignalSourceBinding, ...]:
        if get_signal_by_name(canonical_signal) is None:
            raise KeyError("unregistered canonical vehicle signal: %s" % canonical_signal)
        matches = [
            item for item in self.bindings if item.canonical_signal == canonical_signal
        ]
        matches.sort(
            key=lambda item: (
                -_STATE_RANK[item.state],
                item.priority,
                item.source_kind.value,
                item.source_ref,
            )
        )
        return tuple(matches)

    def preferred_source(
        self, canonical_signal: str
    ) -> Optional[SignalSourceBinding]:
        matches = self.sources_for(canonical_signal)
        return matches[0] if matches else None

    def has_independent_cross_check(self, canonical_signal: str) -> bool:
        verified = [
            item
            for item in self.sources_for(canonical_signal)
            if item.state == EvidenceSourceState.VERIFIED and item.independent
        ]
        source_refs = {item.source_ref for item in verified}
        source_kinds = {item.source_kind for item in verified}
        return len(source_refs) >= 2 and len(source_kinds) >= 2

    def coverage(
        self, canonical_signals: Optional[Iterable[str]] = None
    ) -> Mapping[str, Tuple[str, ...]]:
        names = (
            tuple(canonical_signals)
            if canonical_signals is not None
            else tuple(item.canonical_name for item in CANONICAL_SIGNAL_CATALOG)
        )
        declared = []
        detected = []
        verified = []
        unavailable = []
        for name in names:
            sources = self.sources_for(name)
            if not sources:
                unavailable.append(name)
                continue
            declared.append(name)
            if any(item.state in {EvidenceSourceState.DETECTED, EvidenceSourceState.VERIFIED} for item in sources):
                detected.append(name)
            if any(item.state == EvidenceSourceState.VERIFIED for item in sources):
                verified.append(name)
        return {
            "declared": tuple(declared),
            "detected": tuple(detected),
            "verified": tuple(verified),
            "unavailable": tuple(unavailable),
        }

    def to_dict(self) -> dict[str, Any]:
        coverage = self.coverage()
        return {
            "schema": "velvet.vehicle.evidence_topology.v1",
            "generation": self.generation.value,
            "bindings": [item.to_dict() for item in self.bindings],
            "coverage": {key: list(value) for key, value in coverage.items()},
            "read_only": True,
            "authority": "none",
            "grants_permission": False,
            "grants_authority": False,
            "actuation_granted": False,
            "actuation_performed": False,
        }

    @classmethod
    def from_dict(cls, value: Optional[Mapping[str, Any]]) -> "VehicleEvidenceTopology":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise TypeError("evidence topology must be a mapping")
        raw_bindings = value.get("bindings", ())
        if not isinstance(raw_bindings, (list, tuple)):
            raise TypeError("evidence topology bindings must be a list")
        return cls(
            generation=VehicleGeneration(str(value.get("generation", "unknown"))),
            bindings=tuple(
                SignalSourceBinding.from_dict(item) for item in raw_bindings
            ),
        )

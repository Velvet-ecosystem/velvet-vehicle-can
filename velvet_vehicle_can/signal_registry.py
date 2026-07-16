# SPDX-License-Identifier: GPL-3.0-only
"""Canonical names and lifecycle rules for vehicle CAN observations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SignalLifecycle(str, Enum):
    UNKNOWN = "unknown"
    CANDIDATE = "candidate"
    OBSERVED = "observed"
    CORRELATED = "correlated"
    VALIDATED = "validated"
    QUALIFIED = "qualified"


_LIFECYCLE_ORDER = tuple(SignalLifecycle)


@dataclass(frozen=True)
class SignalCatalogEntry:
    canonical_name: str
    profile_field: str
    description: str
    unit: str | None = None
    default_lifecycle: SignalLifecycle = SignalLifecycle.CANDIDATE
    safety_relevant: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "profile_field": self.profile_field,
            "description": self.description,
            "unit": self.unit,
            "default_lifecycle": self.default_lifecycle.value,
            "safety_relevant": self.safety_relevant,
            "authority": "none",
            "read_only": True,
        }


CANONICAL_SIGNAL_CATALOG: tuple[SignalCatalogEntry, ...] = (
    SignalCatalogEntry("vehicle.speed", "wheel_speed", "Vehicle road speed observation", "km/h", safety_relevant=True),
    SignalCatalogEntry("vehicle.engine.rpm", "engine_rpm", "Engine rotational speed observation", "rpm"),
    SignalCatalogEntry("vehicle.steering.angle", "steering_angle", "Measured steering angle observation", "degree", safety_relevant=True),
    SignalCatalogEntry("vehicle.steering.request", "steering_request", "Observed steering request signal", safety_relevant=True),
    SignalCatalogEntry("vehicle.brake.request", "brake_request", "Observed brake request signal", safety_relevant=True),
    SignalCatalogEntry("vehicle.throttle.request", "throttle_request", "Observed throttle request signal", safety_relevant=True),
    SignalCatalogEntry("vehicle.gear.current", "gear", "Current gear or selector-state observation"),
    SignalCatalogEntry("vehicle.ignition.state", "ignition_state", "Ignition or run-state observation"),
    SignalCatalogEntry("vehicle.door.driver.state", "driver_door", "Driver-door state observation"),
    SignalCatalogEntry("vehicle.diagnostics.o2_fault", "o2_fault", "Observed oxygen-sensor fault state"),
    SignalCatalogEntry("vehicle.cruise.state", "cruise_state", "Cruise-control state observation", safety_relevant=True),
)

_BY_CANONICAL_NAME = {entry.canonical_name: entry for entry in CANONICAL_SIGNAL_CATALOG}
_BY_PROFILE_FIELD = {entry.profile_field: entry for entry in CANONICAL_SIGNAL_CATALOG}


def get_signal_by_name(canonical_name: str) -> SignalCatalogEntry | None:
    return _BY_CANONICAL_NAME.get(canonical_name)


def get_signal_by_profile_field(profile_field: str) -> SignalCatalogEntry | None:
    return _BY_PROFILE_FIELD.get(profile_field)


def canonical_name_for(profile_field: str) -> str:
    entry = get_signal_by_profile_field(profile_field)
    if entry is None:
        raise KeyError(f"unregistered CAN profile field: {profile_field}")
    return entry.canonical_name


def can_transition_signal(
    current: SignalLifecycle,
    target: SignalLifecycle,
) -> bool:
    """Allow holding state or advancing one lifecycle step only.

    Demotion and multi-stage promotion require an explicit external review flow
    rather than an accidental helper call.
    """

    current_index = _LIFECYCLE_ORDER.index(current)
    target_index = _LIFECYCLE_ORDER.index(target)
    return target_index == current_index or target_index == current_index + 1


def validate_catalog(entries: Iterable[SignalCatalogEntry] = CANONICAL_SIGNAL_CATALOG) -> None:
    canonical_names: set[str] = set()
    profile_fields: set[str] = set()

    for entry in entries:
        if not entry.canonical_name.startswith("vehicle."):
            raise ValueError("canonical CAN signal names must start with 'vehicle.'")
        if entry.canonical_name in canonical_names:
            raise ValueError(f"duplicate canonical signal name: {entry.canonical_name}")
        if entry.profile_field in profile_fields:
            raise ValueError(f"duplicate profile field: {entry.profile_field}")
        if not entry.profile_field or "." in entry.profile_field:
            raise ValueError("profile_field must be a non-empty Python-style field name")
        canonical_names.add(entry.canonical_name)
        profile_fields.add(entry.profile_field)


validate_catalog()

# SPDX-License-Identifier: GPL-3.0-only
"""Vehicle hardware capability catalog and conservative state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class CapabilityState(str, Enum):
    ABSENT = "absent"
    DETECTED = "detected"
    INSTALLED = "installed"
    VERIFIED = "verified"
    QUALIFIED = "qualified"
    ENABLED = "enabled"


_STATE_ORDER = tuple(CapabilityState)


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    description: str
    control_related: bool = False
    safety_critical: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "description": self.description,
            "control_related": self.control_related,
            "safety_critical": self.safety_critical,
            "grants_permission": False,
            "grants_authority": False,
        }


@dataclass(frozen=True)
class VehicleCapability:
    capability_id: str
    state: CapabilityState = CapabilityState.ABSENT
    evidence: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "state": self.state.value,
            "evidence": self.evidence,
            "source": self.source,
            "grants_permission": False,
            "grants_authority": False,
            "actuation_granted": False,
        }


VEHICLE_CAPABILITY_CATALOG: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition("vehicle.observe.can", "Receive-only CAN observation"),
    CapabilityDefinition("vehicle.observe.obd2", "OBD-II diagnostics observation"),
    CapabilityDefinition("vehicle.observe.gnss", "GNSS position and time observation"),
    CapabilityDefinition("vehicle.observe.camera.outward", "Outward camera observation"),
    CapabilityDefinition("vehicle.observe.camera.inward", "Inward camera observation"),
    CapabilityDefinition("vehicle.observe.cabin", "Cabin sensor observation"),
    CapabilityDefinition("vehicle.control.steering", "Steering actuator hardware", True, True),
    CapabilityDefinition("vehicle.control.brake", "Brake actuator hardware", True, True),
    CapabilityDefinition("vehicle.control.throttle", "Throttle actuator hardware", True, True),
    CapabilityDefinition("vehicle.control.clutch", "Clutch actuator hardware", True, True),
    CapabilityDefinition("vehicle.control.shifter", "Gear-selection actuator hardware", True, True),
    CapabilityDefinition("vehicle.control.door.lock", "Door-lock control hardware", True, False),
    CapabilityDefinition("vehicle.control.window", "Window control hardware", True, False),
    CapabilityDefinition("vehicle.control.lighting", "Vehicle-light control hardware", True, False),
    CapabilityDefinition("vehicle.control.hvac", "HVAC control hardware", True, False),
)

_BY_ID = {item.capability_id: item for item in VEHICLE_CAPABILITY_CATALOG}


def get_capability_definition(capability_id: str) -> CapabilityDefinition | None:
    return _BY_ID.get(capability_id)


def can_transition_capability(current: CapabilityState, target: CapabilityState) -> bool:
    current_index = _STATE_ORDER.index(current)
    target_index = _STATE_ORDER.index(target)
    return target_index == current_index or target_index == current_index + 1


def transition_capability(
    capability: VehicleCapability,
    target: CapabilityState,
    *,
    evidence: str | None = None,
    source: str | None = None,
) -> VehicleCapability:
    if get_capability_definition(capability.capability_id) is None:
        raise KeyError(f"unregistered vehicle capability: {capability.capability_id}")
    if not can_transition_capability(capability.state, target):
        raise ValueError(
            f"invalid capability transition: {capability.state.value} -> {target.value}"
        )
    return VehicleCapability(
        capability_id=capability.capability_id,
        state=target,
        evidence=evidence if evidence is not None else capability.evidence,
        source=source if source is not None else capability.source,
    )


def validate_capability_catalog(
    entries: Iterable[CapabilityDefinition] = VEHICLE_CAPABILITY_CATALOG,
) -> None:
    seen: set[str] = set()
    for entry in entries:
        if not entry.capability_id.startswith("vehicle."):
            raise ValueError("vehicle capability IDs must start with 'vehicle.'")
        if entry.capability_id in seen:
            raise ValueError(f"duplicate capability ID: {entry.capability_id}")
        if entry.control_related and not entry.capability_id.startswith("vehicle.control."):
            raise ValueError("control-related capabilities must use 'vehicle.control.'")
        seen.add(entry.capability_id)


validate_capability_catalog()

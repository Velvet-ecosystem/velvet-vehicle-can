# SPDX-License-Identifier: GPL-3.0-only
"""Stable read-only event envelopes for decoded CAN observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .signal_decoder import DecodedSignal
from .signal_registry import canonical_name_for


CAN_OBSERVATION_EVENT = "velvet.vehicle.can.signal.observed"
CAN_OBSERVATION_SCHEMA = "velvet.can.observation.v1"


@dataclass(frozen=True)
class CanObservationEvent:
    """One decoded CAN observation prepared for runtime/event transport.

    The envelope deliberately carries no command, requested action, or authority
    field. It describes something Velvet observed, not something she may do.
    """

    signal: str
    profile_field: str
    value: float
    raw_value: int
    confidence: float
    can_id: int
    observed_at: float
    bus_name: str = "obd_can"
    profile_digest: str | None = None

    @classmethod
    def from_decoded_signal(
        cls,
        signal: DecodedSignal,
        *,
        bus_name: str = "obd_can",
        profile_digest: str | None = None,
    ) -> "CanObservationEvent":
        if not bus_name or not bus_name.strip():
            raise ValueError("bus_name must be a non-empty string")
        return cls(
            signal=canonical_name_for(signal.name),
            profile_field=signal.name,
            value=signal.value,
            raw_value=signal.raw_value,
            confidence=signal.confidence,
            can_id=signal.can_id,
            observed_at=signal.timestamp,
            bus_name=bus_name.strip(),
            profile_digest=profile_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": CAN_OBSERVATION_SCHEMA,
            "event": CAN_OBSERVATION_EVENT,
            "source": "velvet-vehicle-can",
            "mode": "read-only",
            "status": "observation-only",
            "observed_at": self.observed_at,
            "bus": self.bus_name,
            "signal": self.signal,
            "profile_field": self.profile_field,
            "value": self.value,
            "raw_value": self.raw_value,
            "confidence": self.confidence,
            "can_id": self.can_id,
            "can_id_hex": f"0x{self.can_id:x}",
            "profile_digest": self.profile_digest,
            "authority": "none",
            "actuation_granted": False,
            "actuation_performed": False,
        }
        return payload


def build_can_observation_events(
    signals: Iterable[DecodedSignal],
    *,
    bus_name: str = "obd_can",
    profile_digest: str | None = None,
    max_events: int = 32,
) -> list[CanObservationEvent]:
    """Convert registered decoded signals into bounded transport envelopes."""

    if isinstance(max_events, bool) or not isinstance(max_events, int):
        raise TypeError("max_events must be an integer")
    if max_events < 1 or max_events > 128:
        raise ValueError("max_events must be between 1 and 128")

    events: list[CanObservationEvent] = []
    for signal in signals:
        events.append(
            CanObservationEvent.from_decoded_signal(
                signal,
                bus_name=bus_name,
                profile_digest=profile_digest,
            )
        )
        if len(events) >= max_events:
            break
    return events


def summarize_can_observation_events(
    events: Iterable[CanObservationEvent],
) -> Mapping[str, Any]:
    items = [event.to_dict() for event in events]
    return {
        "schema": CAN_OBSERVATION_SCHEMA,
        "event": "velvet.vehicle.can.observations",
        "source": "velvet-vehicle-can",
        "mode": "read-only",
        "status": "observation-only",
        "event_count": len(items),
        "events": items,
        "authority": "none",
        "actuation_granted": False,
        "actuation_performed": False,
    }

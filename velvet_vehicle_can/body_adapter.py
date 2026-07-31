# SPDX-License-Identifier: GPL-3.0-only
"""Standard Velvet body records for receive-only CAN hardware.

This adapter translates observed CAN frames into the same SensorPacket and
HealthEvent Event Protocol shapes used by Velvet's simulated body. It exposes no
transmit, send, write, inject, or actuation method.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional
from uuid import uuid4

from .can_observer import ObservedCanFrame, ReceiveOnlyCanObserver


Clock = Callable[[], float]
ReceiptFactory = Callable[[], str]


@dataclass(frozen=True)
class CanBodyAdapterConfig:
    """Stable identity and freshness policy for one receive-only CAN organ."""

    module_id: str = "can-observer"
    node_id: str = "founder-up2"
    owning_handmaiden: str = "Ruby"
    bus_name: str = "obd_can"
    interface_type: str = "socketcan"
    stale_after_ms: int = 2000
    calibration_version: str = "can-observer-v1"
    source_clock: str = "device"

    def __post_init__(self) -> None:
        for name in (
            "module_id",
            "node_id",
            "owning_handmaiden",
            "bus_name",
            "interface_type",
            "calibration_version",
            "source_clock",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("%s must be a non-empty string" % name)
        if isinstance(self.stale_after_ms, bool) or not isinstance(self.stale_after_ms, int):
            raise TypeError("stale_after_ms must be an integer")
        if self.stale_after_ms <= 0:
            raise ValueError("stale_after_ms must be positive")


@dataclass(frozen=True)
class CanBodyCycle:
    """Result of one receive-only CAN body poll."""

    sensor_event: Optional[Mapping[str, Any]] = None
    health_event: Optional[Mapping[str, Any]] = None
    error: Optional[str] = None

    @property
    def observed(self) -> bool:
        return self.sensor_event is not None


class ReceiveOnlyCanBodyAdapter:
    """Translate a receive-only observer into standard body evidence records."""

    def __init__(
        self,
        observer: ReceiveOnlyCanObserver,
        config: Optional[CanBodyAdapterConfig] = None,
        wall_clock: Optional[Clock] = None,
        monotonic_clock: Optional[Clock] = None,
        receipt_factory: Optional[ReceiptFactory] = None,
    ) -> None:
        if not isinstance(observer, ReceiveOnlyCanObserver):
            raise TypeError("observer must be a ReceiveOnlyCanObserver")
        self._observer = observer
        self.config = config or CanBodyAdapterConfig()
        self._wall_clock = wall_clock or time.time
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._receipt_factory = receipt_factory or _new_receipt_id
        self._state = "UNKNOWN"
        self._last_frame_monotonic = None  # type: Optional[float]
        self._stale_reported = False

    @property
    def health_state(self) -> str:
        return self._state

    def poll(self) -> CanBodyCycle:
        """Observe once and emit bounded sensor and health evidence.

        A missing frame is not immediately treated as failure. Once the declared
        stale interval expires, one STALE health transition is emitted. A later
        frame emits RECOVERED and resumes ONLINE sensor packets.
        """

        now_wall = float(self._wall_clock())
        now_monotonic = float(self._monotonic_clock())

        try:
            frame = self._observer.observe()
        except Exception as exc:
            previous = self._state
            self._state = "FAILED"
            self._stale_reported = False
            return CanBodyCycle(
                health_event=self._build_health_event(
                    event_type="FAILED",
                    severity="ERROR",
                    state_before=previous,
                    state_after="FAILED",
                    timestamp=now_wall,
                    confidence=1.0,
                    diagnostic_payload={
                        "error": str(exc),
                        "bus": self.config.bus_name,
                        "read_only": True,
                    },
                    recovery_action="inspect receive-only CAN adapter",
                    fallback_owner="Velvet",
                ),
                error=str(exc),
            )

        if frame is None:
            return self._cycle_without_frame(now_wall, now_monotonic)

        previous = self._state
        health_event = None
        if previous in {"DEGRADED", "FAILED", "RECOVERING"}:
            health_event = self._build_health_event(
                event_type="RECOVERED",
                severity="NOTICE",
                state_before=previous,
                state_after="ONLINE",
                timestamp=now_wall,
                confidence=1.0,
                diagnostic_payload={
                    "bus": self.config.bus_name,
                    "can_id": frame.can_id,
                    "read_only": True,
                },
            )
        elif previous == "UNKNOWN":
            health_event = self._build_health_event(
                event_type="ONLINE",
                severity="INFO",
                state_before="UNKNOWN",
                state_after="ONLINE",
                timestamp=now_wall,
                confidence=1.0,
                diagnostic_payload={
                    "bus": self.config.bus_name,
                    "first_can_id": frame.can_id,
                    "read_only": True,
                },
            )

        self._state = "ONLINE"
        self._last_frame_monotonic = now_monotonic
        self._stale_reported = False
        return CanBodyCycle(
            sensor_event=self._build_sensor_event(frame, now_monotonic),
            health_event=health_event,
        )

    def _cycle_without_frame(self, now_wall: float, now_monotonic: float) -> CanBodyCycle:
        if self._last_frame_monotonic is None:
            return CanBodyCycle()

        age_ms = (now_monotonic - self._last_frame_monotonic) * 1000.0
        if age_ms <= float(self.config.stale_after_ms) or self._stale_reported:
            return CanBodyCycle()

        previous = self._state
        self._state = "DEGRADED"
        self._stale_reported = True
        return CanBodyCycle(
            health_event=self._build_health_event(
                event_type="STALE",
                severity="WARNING",
                state_before=previous,
                state_after="DEGRADED",
                timestamp=now_wall,
                confidence=1.0,
                diagnostic_payload={
                    "bus": self.config.bus_name,
                    "age_ms": age_ms,
                    "stale_after_ms": self.config.stale_after_ms,
                    "read_only": True,
                },
                recovery_action="continue receive-only observation",
                fallback_owner="Velvet",
            )
        )

    def _build_sensor_event(
        self,
        frame: ObservedCanFrame,
        now_monotonic: float,
    ) -> Mapping[str, Any]:
        receipt_id = self._required_receipt_id()
        payload = {
            "module_id": self.config.module_id,
            "node_id": self.config.node_id,
            "owning_handmaiden": self.config.owning_handmaiden,
            "timestamp": float(frame.timestamp),
            "monotonic_time": float(now_monotonic),
            "sensor_type": "can_frame",
            "interface_type": self.config.interface_type,
            "health_state": "ONLINE",
            "confidence": 1.0,
            "payload": {
                "bus": self.config.bus_name,
                "can_id": frame.can_id,
                "can_id_hex": "0x%x" % frame.can_id,
                "data_hex": frame.data_hex,
                "dlc": frame.dlc,
                "extended": frame.extended,
                "read_only": True,
                "actuation_granted": False,
                "actuation_performed": False,
            },
            "receipt_id": receipt_id,
            "source_clock": self.config.source_clock,
            "stale_after_ms": self.config.stale_after_ms,
            "calibration_version": self.config.calibration_version,
            "degraded_reason": None,
            "raw_reference": "%s:%s" % (self.config.bus_name, "0x%x" % frame.can_id),
        }
        return {
            "event_id": receipt_id,
            "event_type": "SENSOR_PACKET_OBSERVED",
            "source": self.config.module_id,
            "family": "sensor",
            "schema_version": "1.0",
            "timestamp": float(frame.timestamp),
            "node_id": self.config.node_id,
            "organ_name": self.config.owning_handmaiden,
            "payload": payload,
        }

    def _build_health_event(
        self,
        event_type: str,
        severity: str,
        state_before: str,
        state_after: str,
        timestamp: float,
        confidence: float,
        diagnostic_payload: Mapping[str, Any],
        recovery_action: Optional[str] = None,
        fallback_owner: Optional[str] = None,
    ) -> Mapping[str, Any]:
        event_id = self._required_receipt_id()
        receipt_id = self._required_receipt_id()
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "module_id": self.config.module_id,
            "node_id": self.config.node_id,
            "owning_handmaiden": self.config.owning_handmaiden,
            "timestamp": float(timestamp),
            "severity": severity,
            "state_before": state_before,
            "state_after": state_after,
            "confidence": float(confidence),
            "diagnostic_payload": dict(diagnostic_payload),
            "receipt_id": receipt_id,
            "recovery_action": recovery_action,
            "fallback_owner": fallback_owner,
        }
        return {
            "event_id": event_id,
            "event_type": "HEALTH_%s" % event_type,
            "source": self.config.module_id,
            "family": "health",
            "schema_version": "1.0",
            "timestamp": float(timestamp),
            "node_id": self.config.node_id,
            "organ_name": self.config.owning_handmaiden,
            "payload": payload,
        }

    def _required_receipt_id(self) -> str:
        value = self._receipt_factory()
        if not isinstance(value, str) or not value.strip():
            raise ValueError("receipt_factory must return a non-empty string")
        return value.strip()


def _new_receipt_id() -> str:
    return str(uuid4())

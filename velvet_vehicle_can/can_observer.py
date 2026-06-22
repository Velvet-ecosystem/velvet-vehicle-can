# SPDX-License-Identifier: GPL-3.0-only
"""Receive-only CAN observation contracts.

This module intentionally exposes no transmit, send, write, inject, or actuation API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .can_backend import CanFrame


@dataclass(frozen=True)
class ObservedCanFrame:
    timestamp: float
    can_id: int
    data_hex: str
    dlc: int
    extended: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "can_id": self.can_id,
            "can_id_hex": f"0x{self.can_id:x}",
            "data_hex": self.data_hex,
            "dlc": self.dlc,
            "extended": self.extended,
            "read_only": True,
            "actuation_performed": False,
        }


class ReceiveOnlyCanObserver:
    """Bounded observation wrapper around a frame-receive callable."""

    def __init__(self, receive: Callable[[], Optional[CanFrame]]) -> None:
        if not callable(receive):
            raise TypeError("receive must be callable")
        self._receive = receive

    def observe(self) -> Optional[ObservedCanFrame]:
        frame = self._receive()
        if frame is None:
            return None
        timestamp, can_id, data = frame
        return normalize_observed_frame(timestamp, can_id, data)


def normalize_observed_frame(timestamp: float, can_id: int, data: bytes) -> ObservedCanFrame:
    if not isinstance(timestamp, (int, float)):
        raise TypeError("timestamp must be numeric")
    if isinstance(can_id, bool) or not isinstance(can_id, int):
        raise TypeError("can_id must be an integer")
    if can_id < 0 or can_id > 0x1FFFFFFF:
        raise ValueError("can_id is outside the CAN 2.0 identifier range")
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if len(data) > 8:
        raise ValueError("classic CAN payload cannot exceed 8 bytes")

    return ObservedCanFrame(
        timestamp=float(timestamp),
        can_id=can_id,
        data_hex=data.hex(),
        dlc=len(data),
        extended=can_id > 0x7FF,
    )

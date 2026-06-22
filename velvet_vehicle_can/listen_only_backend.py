# SPDX-License-Identifier: GPL-3.0-only
"""Linux CAN receive backend with a deliberately receive-only public surface."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .can_backend import CanFrame


@dataclass(frozen=True)
class ListenOnlyCanConfig:
    channel: str = "can0"
    bustype: str = "socketcan"
    receive_timeout_s: float = 0.0

    def __post_init__(self) -> None:
        if not self.channel or self.channel != self.channel.strip():
            raise ValueError("channel must be a non-empty normalized string")
        if not self.bustype or self.bustype != self.bustype.strip():
            raise ValueError("bustype must be a non-empty normalized string")
        if self.receive_timeout_s < 0:
            raise ValueError("receive_timeout_s cannot be negative")


class ListenOnlyPythonCanReader:
    """Receive-only public adapter backed by python-can.

    The underlying bus remains private and is requested in PASSIVE state when
    the installed python-can backend supports it. This class intentionally has
    no send, transmit, write, or inject method.

    Linux deployment must also configure the CAN interface in kernel listen-only
    mode. Application-level wrapping is not a substitute for that physical host
    configuration.
    """

    def __init__(self, config: ListenOnlyCanConfig) -> None:
        try:
            import can  # type: ignore
        except Exception as exc:
            raise RuntimeError("python-can is required for ListenOnlyPythonCanReader") from exc

        kwargs = {
            "channel": config.channel,
            "interface": config.bustype,
            "receive_own_messages": False,
        }
        passive = getattr(getattr(can, "BusState", None), "PASSIVE", None)
        if passive is not None:
            kwargs["state"] = passive

        self._bus = can.Bus(**kwargs)
        self._timeout = config.receive_timeout_s

    def read_frame(self) -> Optional[CanFrame]:
        message = self._bus.recv(timeout=self._timeout)
        if message is None:
            return None
        timestamp = float(getattr(message, "timestamp", time.time()))
        can_id = int(message.arbitration_id)
        data = bytes(message.data) if message.data is not None else b""
        return timestamp, can_id, data

    def shutdown(self) -> None:
        try:
            self._bus.shutdown()
        except Exception:
            pass

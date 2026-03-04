from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Protocol
import time
import logging

logger = logging.getLogger(__name__)

# (ts, can_id, data)
CanFrame = Tuple[float, int, bytes]


class CanReader(Protocol):
    """
    Minimal read-only CAN interface for CanSnifferService.
    """
    def read_frame(self) -> Optional[CanFrame]:
        ...


@dataclass
class SocketCanConfig:
    """
    SocketCAN interface config.

    Common Linux interfaces:
      - can0, can1 (native)
      - vcan0 (virtual for testing)
    """
    channel: str = "can0"
    bustype: str = "socketcan"
    receive_timeout_s: float = 0.0  # 0.0 = non-blocking
    bitrate: Optional[int] = None   # usually set via `ip link`, not here


class PythonCanReader(CanReader):
    """
    Read-only CAN reader using python-can.
    """
    def __init__(self, cfg: SocketCanConfig) -> None:
        try:
            import can  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "python-can is required for PythonCanReader. "
                "Install it (pip install python-can) and ensure SocketCAN is configured."
            ) from e

        self._can = can
        self.cfg = cfg
        self.bus = can.interface.Bus(channel=cfg.channel, bustype=cfg.bustype)
        logger.info(f"[can] PythonCanReader online bustype={cfg.bustype} channel={cfg.channel}")

    def read_frame(self) -> Optional[CanFrame]:
        """
        Non-blocking by default. Returns (ts, can_id, data) or None.
        """
        msg = self.bus.recv(timeout=self.cfg.receive_timeout_s)
        if msg is None:
            return None

        ts = float(getattr(msg, "timestamp", time.time()))
        can_id = int(msg.arbitration_id)
        data = bytes(msg.data) if msg.data is not None else b""
        return (ts, can_id, data)

    def shutdown(self) -> None:
        try:
            self.bus.shutdown()
        except Exception:
            pass


class FakeCanReader(CanReader):
    """
    A tiny virtual reader for tests / demos. Feed frames via `push()`.
    """
    def __init__(self) -> None:
        from collections import deque
        self._q = deque()

    def push(self, can_id: int, data: bytes, ts: Optional[float] = None) -> None:
        self._q.append((ts or time.time(), can_id, data))

    def read_frame(self) -> Optional[CanFrame]:
        if not self._q:
            return None
        return self._q.popleft()

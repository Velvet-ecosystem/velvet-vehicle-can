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
    """Legacy receive API delegated to the verified backend; no public raw bus."""
    def __init__(self, cfg: SocketCanConfig) -> None:
        from .listen_only_backend import ListenOnlyCanConfig, ListenOnlyPythonCanReader
        self._reader = ListenOnlyPythonCanReader(ListenOnlyCanConfig(
            channel=cfg.channel, bustype=cfg.bustype, receive_timeout_s=cfg.receive_timeout_s,
        ))

    def read_frame(self) -> Optional[CanFrame]:
        return self._reader.read_frame()

    def shutdown(self) -> None:
        self._reader.shutdown()


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

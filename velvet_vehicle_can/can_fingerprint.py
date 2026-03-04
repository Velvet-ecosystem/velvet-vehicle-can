from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple
import hashlib
import time


@dataclass(frozen=True)
class CanIdStats:
    """Basic per-arbitration-ID stats used for fingerprinting."""
    hz: float
    payload_len: int
    variability: float  # 0..1 rough measure of changing bytes


@dataclass
class CanFingerprint:
    """
    Stable-ish signature of a vehicle's CAN behavior.
    Do not store raw VIN in plaintext by default; store vin_hash.
    """
    vin_hash: Optional[str] = None
    bus_name: str = "obd_can"
    created_at: float = field(default_factory=lambda: time.time())
    id_stats: Dict[int, CanIdStats] = field(default_factory=dict)
    checksum_like_ids: Tuple[int, ...] = ()
    counter_like_ids: Tuple[int, ...] = ()

    def digest(self) -> str:
        """A compact digest for matching (not cryptographic authentication)."""
        h = hashlib.sha256()
        h.update((self.vin_hash or "").encode("utf-8"))
        h.update(self.bus_name.encode("utf-8"))

        # Sort for stability
        for can_id in sorted(self.id_stats.keys()):
            s = self.id_stats[can_id]
            h.update(str(can_id).encode("utf-8"))
            h.update(f"{s.hz:.3f},{s.payload_len},{s.variability:.4f}".encode("utf-8"))

        h.update(",".join(map(str, self.checksum_like_ids)).encode("utf-8"))
        h.update(",".join(map(str, self.counter_like_ids)).encode("utf-8"))
        return h.hexdigest()[:24]


def hash_vin(vin: str) -> str:
    """Privacy-preserving VIN hash (salt can be added later)."""
    vin = vin.strip().upper()
    return hashlib.sha256(vin.encode("utf-8")).hexdigest()


class CanFingerprintBuilder:
    """
    Build a fingerprint from timestamped CAN frames.

    Frames should be tuples: (timestamp_seconds, can_id, data_bytes)
    """
    def __init__(self, bus_name: str = "obd_can") -> None:
        self.bus_name = bus_name

    def build(
        self,
        frames: Iterable[Tuple[float, int, bytes]],
        vin: Optional[str] = None,
        window_seconds: float = 30.0,
    ) -> CanFingerprint:
        """
        Compute per-ID frequency and basic payload variability in a window.
        """
        now = None
        recent = []
        for ts, can_id, data in frames:
            now = ts if now is None else max(now, ts)
            recent.append((ts, can_id, data))

        if now is None:
            return CanFingerprint(vin_hash=hash_vin(vin) if vin else None, bus_name=self.bus_name)

        start = now - window_seconds
        recent = [(ts, cid, data) for (ts, cid, data) in recent if ts >= start]

        # Stats
        counts: Dict[int, int] = {}
        last_ts: Dict[int, float] = {}
        lens: Dict[int, int] = {}
        byte_changes: Dict[int, float] = {}
        last_data: Dict[int, bytes] = {}

        for ts, cid, data in recent:
            counts[cid] = counts.get(cid, 0) + 1
            lens[cid] = len(data)
            if cid in last_data:
                # variability heuristic: fraction of bytes that changed
                prev = last_data[cid]
                diff = sum(1 for a, b in zip(prev, data) if a != b)
                denom = max(1, min(len(prev), len(data)))
                byte_changes[cid] = byte_changes.get(cid, 0.0) + (diff / denom)
            last_data[cid] = data
            last_ts[cid] = ts

        id_stats: Dict[int, CanIdStats] = {}
        duration = max(1e-6, (now - start))
        for cid, c in counts.items():
            hz = c / duration
            variability = 0.0
            if c > 1:
                variability = min(1.0, byte_changes.get(cid, 0.0) / (c - 1))
            id_stats[cid] = CanIdStats(hz=hz, payload_len=lens.get(cid, 0), variability=variability)

        # TODO: enrich these lists by detecting counter/checksum patterns
        fp = CanFingerprint(
            vin_hash=hash_vin(vin) if vin else None,
            bus_name=self.bus_name,
            id_stats=id_stats,
            checksum_like_ids=tuple(),
            counter_like_ids=tuple(),
        )
        return fp

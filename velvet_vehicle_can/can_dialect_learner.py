from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import math

from .vehicle_profile import SignalDef, SignalMap, IntegrityRule


@dataclass
class LabeledEvent:
    """
    A short time window where a driver action is known/assumed.

    action examples:
      - "steer_left_sweep"
      - "steer_right_sweep"
      - "brake_press"
      - "throttle_increase"
      - "steady_cruise"
    """
    start_ts: float
    end_ts: float
    action: str


@dataclass
class TelemetrySample:
    """
    Non-CAN ground truth signals (optional but powerful).
    """
    ts: float
    yaw_rate: Optional[float] = None
    accel_x: Optional[float] = None
    gps_speed: Optional[float] = None


CanFrame = Tuple[float, int, bytes]  # (ts, can_id, data)


class CanDialectLearner:
    """
    Learns candidate SignalDefs by correlating labeled driver events + motion telemetry
    with CAN frame/byte changes.

    This is intentionally conservative: it proposes candidates with confidence scores.
    Another layer must validate (shadow mode) before any injection is permitted.
    """

    def __init__(self) -> None:
        pass

    def learn_signal_map(
        self,
        frames: Iterable[CanFrame],
        labeled_events: List[LabeledEvent],
        telemetry: Optional[List[TelemetrySample]] = None,
    ) -> SignalMap:
        frames_list = list(frames)
        # 1) basic per-ID variability in labeled windows
        per_action_candidates: Dict[str, List[Tuple[int, float]]] = {}

        for ev in labeled_events:
            window = [f for f in frames_list if ev.start_ts <= f[0] <= ev.end_ts]
            scores = self._score_ids_by_variability(window)
            per_action_candidates[ev.action] = scores

        # 2) pick top candidates per action (placeholders)
        # In real implementation, we'd go down to byte-level scoring and field extraction.
        sm = SignalMap()

        # Heuristic placeholders:
        steer_left = per_action_candidates.get("steer_left_sweep") or []
        steer_right = per_action_candidates.get("steer_right_sweep") or []
        brake = per_action_candidates.get("brake_press") or []
        throttle = per_action_candidates.get("throttle_increase") or []

        # If left/right point to same ID, it's a strong hint for steering-related frames.
        steering_id = self._common_top_id(steer_left, steer_right)
        if steering_id is not None:
            sm.steering_angle = SignalDef(
                can_id=steering_id,
                start=0,
                length=2,
                endian="little",
                signed=True,
                scale=1.0,
                offset=0.0,
                integrity=IntegrityRule(),
                confidence=0.25,  # low until byte-level extraction + validation
            )

        if brake:
            sm.brake_request = SignalDef(
                can_id=brake[0][0],
                start=0,
                length=2,
                endian="little",
                signed=False,
                scale=1.0,
                offset=0.0,
                integrity=IntegrityRule(),
                confidence=0.20,
            )

        if throttle:
            sm.throttle_request = SignalDef(
                can_id=throttle[0][0],
                start=0,
                length=2,
                endian="little",
                signed=False,
                scale=1.0,
                offset=0.0,
                integrity=IntegrityRule(),
                confidence=0.20,
            )

        # Wheel speed is often discoverable even without labels; here we leave it None by default.
        return sm

    def _score_ids_by_variability(self, window_frames: List[CanFrame]) -> List[Tuple[int, float]]:
        """
        Returns list of (can_id, score) sorted by score desc.
        Score is a simple payload-change heuristic; replace with byte-level correlation later.
        """
        last: Dict[int, bytes] = {}
        change_sum: Dict[int, float] = {}
        count: Dict[int, int] = {}

        for _, cid, data in window_frames:
            count[cid] = count.get(cid, 0) + 1
            if cid in last:
                prev = last[cid]
                denom = max(1, min(len(prev), len(data)))
                diff = sum(1 for a, b in zip(prev, data) if a != b) / denom
                change_sum[cid] = change_sum.get(cid, 0.0) + diff
            last[cid] = data

        scored = []
        for cid, c in count.items():
            if c < 3:
                continue
            avg_change = change_sum.get(cid, 0.0) / max(1, c - 1)
            scored.append((cid, avg_change))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:25]

    def _common_top_id(
        self,
        a: List[Tuple[int, float]],
        b: List[Tuple[int, float]],
        top_n: int = 5,
    ) -> Optional[int]:
        a_ids = [cid for cid, _ in a[:top_n]]
        b_ids = [cid for cid, _ in b[:top_n]]
        for cid in a_ids:
            if cid in b_ids:
                return cid
        return None

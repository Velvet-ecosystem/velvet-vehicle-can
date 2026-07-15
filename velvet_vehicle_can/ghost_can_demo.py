# SPDX-License-Identifier: GPL-3.0-only
"""Public-safe ghost CAN demo for Velvet Vehicle CAN."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .can_backend import FakeCanReader
from .can_observer import ObservedCanFrame, ReceiveOnlyCanObserver
from .signal_decoder import decode_signal_map, summarize_decoded_signals
from .vehicle_profile import SignalDef, SignalMap

GHOST_SIGNAL_MAP = SignalMap(
    wheel_speed=SignalDef(can_id=0x120, start=0, length=2, endian="little", scale=0.01, confidence=0.98),
    engine_rpm=SignalDef(can_id=0x121, start=0, length=2, endian="little", scale=0.25, confidence=0.96),
    steering_angle=SignalDef(can_id=0x122, start=0, length=2, endian="little", signed=True, scale=0.1, confidence=0.94),
    gear=SignalDef(can_id=0x123, start=0, length=1, endian="little", confidence=0.90),
    ignition_state=SignalDef(can_id=0x124, start=0, length=1, endian="little", confidence=0.93),
    driver_door=SignalDef(can_id=0x125, start=0, length=1, endian="little", confidence=0.91),
    o2_fault=SignalDef(can_id=0x126, start=0, length=1, endian="little", confidence=0.89),
)

DEFAULT_GHOST_FRAMES = (
    {"timestamp": 1.00, "can_id": "0x120", "data_hex": "0000000000000000"},
    {"timestamp": 1.01, "can_id": "0x121", "data_hex": "a00f000000000000"},
    {"timestamp": 1.02, "can_id": "0x122", "data_hex": "0000000000000000"},
    {"timestamp": 1.03, "can_id": "0x123", "data_hex": "0100000000000000"},
    {"timestamp": 1.04, "can_id": "0x124", "data_hex": "0000000000000000"},
    {"timestamp": 1.05, "can_id": "0x125", "data_hex": "0000000000000000"},
    {"timestamp": 1.06, "can_id": "0x126", "data_hex": "0100000000000000"},
)

def parse_can_id(value):
    if isinstance(value, int): return value
    if not isinstance(value, str): raise TypeError("can_id must be an integer or string")
    return int(value, 0)

def load_ghost_frames(path=None):
    if path is None: return [dict(item) for item in DEFAULT_GHOST_FRAMES]
    frames=[]
    for line_number,line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped=line.strip()
        if not stripped or stripped.startswith("#"): continue
        try: frames.append(json.loads(stripped))
        except json.JSONDecodeError as exc: raise ValueError(f"invalid JSONL ghost frame at line {line_number}: {exc}") from exc
    return frames

def observe_ghost_frames(frames: Iterable[dict[str, Any]]) -> list[ObservedCanFrame]:
    reader=FakeCanReader(); base_ts=time.time()
    for index,frame in enumerate(frames):
        reader.push(can_id=parse_can_id(frame["can_id"]), data=bytes.fromhex(str(frame["data_hex"])), ts=float(frame.get("timestamp", base_ts+index*0.01)))
    observer=ReceiveOnlyCanObserver(reader.read_frame); observed=[]
    while True:
        item=observer.observe()
        if item is None: break
        observed.append(item)
    return observed

def build_ghost_event(frames=None):
    observed=observe_ghost_frames(frames or DEFAULT_GHOST_FRAMES)
    decoded=decode_signal_map(observed, GHOST_SIGNAL_MAP, minimum_confidence=0.0, max_signals=32)
    return {"event_type":"vehicle.can.ghost_observation","mode":"ghost-demo","source":"velvet-vehicle-can","frame_count":len(observed),"frames":[frame.to_dict() for frame in observed],"decoded_summary":summarize_decoded_signals(decoded),"read_only":True,"hardware_bus_opened":False,"actuation_granted":False,"actuation_performed":False,"receipt_hint":"safe public ghost CAN loop: synthetic frames -> observation -> decode -> receipt"}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Run Velvet's public-safe ghost CAN demo.")
    parser.add_argument("--fixture"); parser.add_argument("--pretty", action="store_true")
    args=parser.parse_args(argv)
    event=build_ghost_event(load_ghost_frames(args.fixture) if args.fixture else load_ghost_frames())
    print(json.dumps(event, indent=2 if args.pretty else None, sort_keys=True)); return 0

if __name__ == "__main__":
    raise SystemExit(main())

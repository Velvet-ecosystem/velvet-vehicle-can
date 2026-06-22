# SPDX-License-Identifier: GPL-3.0-only
"""Conservative read-only decoding of learned CAN signal definitions."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Iterable, Mapping

from .can_observer import ObservedCanFrame
from .vehicle_profile import SignalDef, SignalMap


@dataclass(frozen=True)
class DecodedSignal:
    """One interpreted observation derived from a learned signal definition."""

    name: str
    value: float
    raw_value: int
    confidence: float
    can_id: int
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "raw_value": self.raw_value,
            "confidence": self.confidence,
            "can_id": self.can_id,
            "can_id_hex": f"0x{self.can_id:x}",
            "timestamp": self.timestamp,
            "source": "learned-can-profile",
            "status": "observation-only",
            "read_only": True,
            "actuation_granted": False,
            "actuation_performed": False,
        }


def decode_signal(
    frame: ObservedCanFrame,
    *,
    name: str,
    definition: SignalDef,
    minimum_confidence: float = 0.0,
) -> DecodedSignal | None:
    """Decode one byte-aligned signal when the frame and confidence match."""

    _validate_definition(definition)
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum_confidence must be between 0 and 1")
    if definition.confidence < minimum_confidence:
        return None
    if frame.can_id != definition.can_id:
        return None

    payload = bytes.fromhex(frame.data_hex)
    end = definition.start + definition.length
    if end > len(payload):
        return None

    raw_bytes = payload[definition.start:end]
    raw_value = int.from_bytes(
        raw_bytes,
        byteorder=definition.endian,
        signed=definition.signed,
    )
    value = raw_value * definition.scale + definition.offset
    return DecodedSignal(
        name=name,
        value=float(value),
        raw_value=raw_value,
        confidence=float(definition.confidence),
        can_id=frame.can_id,
        timestamp=frame.timestamp,
    )


def decode_signal_map(
    frames_in: Iterable[ObservedCanFrame],
    signal_map: SignalMap,
    *,
    minimum_confidence: float = 0.0,
    max_signals: int = 32,
) -> list[DecodedSignal]:
    """Return the latest bounded decoded observation for each known signal."""

    if isinstance(max_signals, bool) or not isinstance(max_signals, int):
        raise TypeError("max_signals must be an integer")
    if max_signals < 1 or max_signals > 128:
        raise ValueError("max_signals must be between 1 and 128")

    frames_by_id: dict[int, ObservedCanFrame] = {}
    for frame in frames_in:
        current = frames_by_id.get(frame.can_id)
        if current is None or frame.timestamp >= current.timestamp:
            frames_by_id[frame.can_id] = frame

    decoded: list[DecodedSignal] = []
    for item in fields(signal_map):
        definition = getattr(signal_map, item.name)
        if definition is None:
            continue
        frame = frames_by_id.get(definition.can_id)
        if frame is None:
            continue
        result = decode_signal(
            frame,
            name=item.name,
            definition=definition,
            minimum_confidence=minimum_confidence,
        )
        if result is not None:
            decoded.append(result)
        if len(decoded) >= max_signals:
            break
    return decoded


def summarize_decoded_signals(signals: Iterable[DecodedSignal]) -> Mapping[str, Any]:
    items = [signal.to_dict() for signal in signals]
    return {
        "mode": "read-only",
        "status": "observation-only",
        "signal_count": len(items),
        "signals": items,
        "actuation_granted": False,
        "actuation_performed": False,
    }


def _validate_definition(definition: SignalDef) -> None:
    if isinstance(definition.start, bool) or not isinstance(definition.start, int):
        raise TypeError("signal start must be an integer byte offset")
    if isinstance(definition.length, bool) or not isinstance(definition.length, int):
        raise TypeError("signal length must be an integer byte length")
    if definition.start < 0:
        raise ValueError("signal start cannot be negative")
    if definition.length < 1 or definition.length > 8:
        raise ValueError("signal length must be between 1 and 8 bytes")
    if definition.start + definition.length > 8:
        raise ValueError("signal definition exceeds classic CAN payload bounds")
    if definition.endian not in {"little", "big"}:
        raise ValueError("signal endian must be 'little' or 'big'")
    if not 0.0 <= definition.confidence <= 1.0:
        raise ValueError("signal confidence must be between 0 and 1")

# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.can_observer import ObservedCanFrame
from velvet_vehicle_can.signal_decoder import (
    decode_signal,
    decode_signal_map,
    summarize_decoded_signals,
)
from velvet_vehicle_can.vehicle_profile import SignalDef, SignalMap


class TestSignalDecoder(unittest.TestCase):
    def test_decodes_little_endian_scaled_signal(self):
        frame = ObservedCanFrame(
            timestamp=10.0,
            can_id=0x123,
            data_hex="3412000000000000",
            dlc=8,
            extended=False,
        )
        definition = SignalDef(
            can_id=0x123,
            start=0,
            length=2,
            endian="little",
            scale=0.1,
            offset=1.0,
            confidence=0.9,
        )

        result = decode_signal(frame, name="wheel_speed", definition=definition)

        self.assertIsNotNone(result)
        self.assertEqual(result.raw_value, 0x1234)
        self.assertAlmostEqual(result.value, 467.0)
        self.assertEqual(result.to_dict()["status"], "observation-only")
        self.assertFalse(result.to_dict()["actuation_granted"])
        self.assertFalse(result.to_dict()["actuation_performed"])

    def test_decodes_signed_big_endian_signal(self):
        frame = ObservedCanFrame(
            timestamp=11.0,
            can_id=0x124,
            data_hex="ff9c",
            dlc=2,
            extended=False,
        )
        definition = SignalDef(
            can_id=0x124,
            start=0,
            length=2,
            endian="big",
            signed=True,
            confidence=1.0,
        )

        result = decode_signal(frame, name="steering_angle", definition=definition)

        self.assertEqual(result.raw_value, -100)
        self.assertEqual(result.value, -100.0)

    def test_confidence_and_frame_mismatch_fail_closed(self):
        frame = ObservedCanFrame(1.0, 0x100, "01", 1, False)
        definition = SignalDef(can_id=0x101, start=0, length=1, confidence=0.4)

        self.assertIsNone(decode_signal(frame, name="gear", definition=definition))

        definition.can_id = 0x100
        self.assertIsNone(
            decode_signal(
                frame,
                name="gear",
                definition=definition,
                minimum_confidence=0.5,
            )
        )

    def test_short_payload_returns_no_observation(self):
        frame = ObservedCanFrame(1.0, 0x100, "01", 1, False)
        definition = SignalDef(can_id=0x100, start=0, length=2, confidence=1.0)

        self.assertIsNone(decode_signal(frame, name="gear", definition=definition))

    def test_signal_map_uses_latest_frame_and_bounded_output(self):
        signal_map = SignalMap(
            wheel_speed=SignalDef(can_id=0x200, start=0, length=1, confidence=0.8),
            gear=SignalDef(can_id=0x201, start=0, length=1, confidence=0.9),
        )
        frames = [
            ObservedCanFrame(1.0, 0x200, "01", 1, False),
            ObservedCanFrame(2.0, 0x200, "02", 1, False),
            ObservedCanFrame(3.0, 0x201, "03", 1, False),
        ]

        decoded = decode_signal_map(frames, signal_map, max_signals=1)

        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].name, "wheel_speed")
        self.assertEqual(decoded[0].raw_value, 2)

    def test_summary_never_claims_authority(self):
        signal_map = SignalMap(
            gear=SignalDef(can_id=0x201, start=0, length=1, confidence=1.0),
        )
        frame = ObservedCanFrame(3.0, 0x201, "03", 1, False)
        summary = summarize_decoded_signals(decode_signal_map([frame], signal_map))

        self.assertEqual(summary["signal_count"], 1)
        self.assertEqual(summary["mode"], "read-only")
        self.assertEqual(summary["status"], "observation-only")
        self.assertFalse(summary["actuation_granted"])
        self.assertFalse(summary["actuation_performed"])

    def test_invalid_definition_is_rejected(self):
        frame = ObservedCanFrame(1.0, 0x100, "00", 1, False)
        definition = SignalDef(can_id=0x100, start=7, length=2, confidence=1.0)

        with self.assertRaises(ValueError):
            decode_signal(frame, name="gear", definition=definition)


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.can_events import (
    CAN_OBSERVATION_EVENT,
    CAN_OBSERVATION_SCHEMA,
    CanObservationEvent,
    build_can_observation_events,
    summarize_can_observation_events,
)
from velvet_vehicle_can.signal_decoder import DecodedSignal


class TestCanObservationEvents(unittest.TestCase):
    def setUp(self):
        self.signal = DecodedSignal(
            name="wheel_speed",
            value=42.5,
            raw_value=425,
            confidence=0.91,
            can_id=0x200,
            timestamp=12.5,
        )

    def test_event_preserves_provenance_and_denies_authority(self):
        event = CanObservationEvent.from_decoded_signal(
            self.signal,
            bus_name="powertrain_can",
            profile_digest="abc123",
        )
        payload = event.to_dict()

        self.assertEqual(payload["schema"], CAN_OBSERVATION_SCHEMA)
        self.assertEqual(payload["event"], CAN_OBSERVATION_EVENT)
        self.assertEqual(payload["source"], "velvet-vehicle-can")
        self.assertEqual(payload["bus"], "powertrain_can")
        self.assertEqual(payload["profile_digest"], "abc123")
        self.assertEqual(payload["signal"], "wheel_speed")
        self.assertEqual(payload["can_id_hex"], "0x200")
        self.assertEqual(payload["authority"], "none")
        self.assertFalse(payload["actuation_granted"])
        self.assertFalse(payload["actuation_performed"])

    def test_blank_bus_name_fails_closed(self):
        with self.assertRaises(ValueError):
            CanObservationEvent.from_decoded_signal(self.signal, bus_name="   ")

    def test_builder_is_bounded(self):
        signals = [self.signal, self.signal, self.signal]
        events = build_can_observation_events(signals, max_events=2)
        self.assertEqual(len(events), 2)

    def test_invalid_event_bound_is_rejected(self):
        with self.assertRaises(TypeError):
            build_can_observation_events([self.signal], max_events=True)
        with self.assertRaises(ValueError):
            build_can_observation_events([self.signal], max_events=0)
        with self.assertRaises(ValueError):
            build_can_observation_events([self.signal], max_events=129)

    def test_summary_remains_observation_only(self):
        events = build_can_observation_events([self.signal])
        summary = summarize_can_observation_events(events)

        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["mode"], "read-only")
        self.assertEqual(summary["status"], "observation-only")
        self.assertEqual(summary["authority"], "none")
        self.assertFalse(summary["actuation_granted"])
        self.assertFalse(summary["actuation_performed"])


if __name__ == "__main__":
    unittest.main()

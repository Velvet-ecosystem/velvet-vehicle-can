# SPDX-License-Identifier: GPL-3.0-only

import json
import subprocess
import sys
import unittest

from velvet_vehicle_can.ghost_can_demo import build_ghost_event, observe_ghost_frames


class TestGhostCanDemo(unittest.TestCase):
    def test_ghost_event_is_observation_only(self):
        event = build_ghost_event()
        self.assertEqual(event["event_type"], "vehicle.can.ghost_observation")
        self.assertTrue(event["read_only"])
        self.assertFalse(event["hardware_bus_opened"])
        self.assertFalse(event["actuation_granted"])
        self.assertFalse(event["actuation_performed"])
        self.assertGreater(event["frame_count"], 0)
        self.assertGreater(event["decoded_summary"]["signal_count"], 0)
        self.assertFalse(event["decoded_summary"]["actuation_performed"])

    def test_observed_frames_keep_receive_only_flags(self):
        frames = observe_ghost_frames([{"timestamp": 1.0, "can_id": "0x120", "data_hex": "0000"}])
        self.assertEqual(len(frames), 1)
        frame_dict = frames[0].to_dict()
        self.assertTrue(frame_dict["read_only"])
        self.assertFalse(frame_dict["actuation_performed"])

    def test_module_cli_outputs_json(self):
        result = subprocess.run([sys.executable, "-m", "velvet_vehicle_can.ghost_can_demo"], check=True, capture_output=True, text=True)
        event = json.loads(result.stdout)
        self.assertEqual(event["event_type"], "vehicle.can.ghost_observation")
        self.assertFalse(event["hardware_bus_opened"])


if __name__ == "__main__":
    unittest.main()

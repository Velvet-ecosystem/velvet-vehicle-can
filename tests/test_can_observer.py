import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from velvet_vehicle_can.can_observer import ReceiveOnlyCanObserver, normalize_observed_frame


class TestReceiveOnlyCanObserver(unittest.TestCase):
    def test_observes_bounded_classic_frame(self):
        observer = ReceiveOnlyCanObserver(lambda: (12.5, 0x123, b"\x01\x02"))
        frame = observer.observe()
        self.assertEqual(frame.can_id, 0x123)
        self.assertEqual(frame.data_hex, "0102")
        self.assertEqual(frame.dlc, 2)
        self.assertFalse(frame.extended)
        self.assertTrue(frame.to_dict()["read_only"])
        self.assertFalse(frame.to_dict()["actuation_performed"])

    def test_observer_exposes_no_transmit_surface(self):
        observer = ReceiveOnlyCanObserver(lambda: None)
        for name in ("send", "transmit", "write", "inject", "actuate"):
            self.assertFalse(hasattr(observer, name), name)

    def test_rejects_invalid_identifier(self):
        with self.assertRaises(ValueError):
            normalize_observed_frame(1.0, 0x20000000, b"")

    def test_rejects_oversized_classic_payload(self):
        with self.assertRaises(ValueError):
            normalize_observed_frame(1.0, 0x123, b"123456789")


if __name__ == "__main__":
    unittest.main()

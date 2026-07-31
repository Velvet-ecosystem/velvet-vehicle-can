import unittest

from velvet_vehicle_can import (
    CanBodyAdapterConfig,
    FakeCanReader,
    ReceiveOnlyCanBodyAdapter,
    ReceiveOnlyCanObserver,
)


class MutableClock:
    def __init__(self, value):
        self.value = float(value)

    def __call__(self):
        return self.value


class ReceiptSequence:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return "receipt-%d" % self.count


class ReceiveOnlyCanBodyAdapterTests(unittest.TestCase):
    def make_adapter(self, reader, wall=None, mono=None, receipts=None, stale_after_ms=2000):
        observer = ReceiveOnlyCanObserver(reader.read_frame)
        return ReceiveOnlyCanBodyAdapter(
            observer,
            CanBodyAdapterConfig(stale_after_ms=stale_after_ms),
            wall_clock=wall or MutableClock(200.0),
            monotonic_clock=mono or MutableClock(10.0),
            receipt_factory=receipts or ReceiptSequence(),
        )

    def test_live_frame_emits_standard_sensor_and_online_health(self):
        reader = FakeCanReader()
        reader.push(0x123, b"\x01\x02", ts=100.0)
        adapter = self.make_adapter(reader)

        cycle = adapter.poll()

        self.assertTrue(cycle.observed)
        self.assertEqual(cycle.sensor_event["family"], "sensor")
        self.assertEqual(cycle.sensor_event["event_type"], "SENSOR_PACKET_OBSERVED")
        packet = cycle.sensor_event["payload"]
        self.assertEqual(packet["module_id"], "can-observer")
        self.assertEqual(packet["node_id"], "founder-up2")
        self.assertEqual(packet["owning_handmaiden"], "Ruby")
        self.assertEqual(packet["sensor_type"], "can_frame")
        self.assertEqual(packet["payload"]["can_id"], 0x123)
        self.assertEqual(packet["payload"]["data_hex"], "0102")
        self.assertTrue(packet["payload"]["read_only"])
        self.assertFalse(packet["payload"]["actuation_granted"])
        self.assertEqual(cycle.health_event["payload"]["event_type"], "ONLINE")
        self.assertEqual(adapter.health_state, "ONLINE")

    def test_stale_transition_emits_once(self):
        reader = FakeCanReader()
        mono = MutableClock(10.0)
        reader.push(0x100, b"\x00", ts=100.0)
        adapter = self.make_adapter(reader, mono=mono, stale_after_ms=1000)
        adapter.poll()

        mono.value = 11.5
        stale = adapter.poll()
        repeated = adapter.poll()

        self.assertEqual(stale.health_event["payload"]["event_type"], "STALE")
        self.assertEqual(stale.health_event["payload"]["state_after"], "DEGRADED")
        self.assertIsNone(repeated.health_event)
        self.assertEqual(adapter.health_state, "DEGRADED")

    def test_frame_after_stale_emits_recovered(self):
        reader = FakeCanReader()
        mono = MutableClock(10.0)
        reader.push(0x100, b"\x00", ts=100.0)
        adapter = self.make_adapter(reader, mono=mono, stale_after_ms=1000)
        adapter.poll()
        mono.value = 11.5
        adapter.poll()

        reader.push(0x101, b"\x01", ts=102.0)
        mono.value = 11.6
        recovered = adapter.poll()

        self.assertTrue(recovered.observed)
        self.assertEqual(recovered.health_event["payload"]["event_type"], "RECOVERED")
        self.assertEqual(recovered.health_event["payload"]["state_before"], "DEGRADED")
        self.assertEqual(recovered.health_event["payload"]["state_after"], "ONLINE")
        self.assertEqual(adapter.health_state, "ONLINE")

    def test_reader_exception_becomes_failed_health_evidence(self):
        def broken_reader():
            raise RuntimeError("CAN device disappeared")

        adapter = ReceiveOnlyCanBodyAdapter(
            ReceiveOnlyCanObserver(broken_reader),
            wall_clock=MutableClock(200.0),
            monotonic_clock=MutableClock(10.0),
            receipt_factory=ReceiptSequence(),
        )

        cycle = adapter.poll()

        self.assertFalse(cycle.observed)
        self.assertIn("CAN device disappeared", cycle.error)
        self.assertEqual(cycle.health_event["payload"]["event_type"], "FAILED")
        self.assertEqual(cycle.health_event["payload"]["state_after"], "FAILED")
        self.assertEqual(adapter.health_state, "FAILED")

    def test_adapter_has_no_transmit_surface(self):
        reader = FakeCanReader()
        adapter = self.make_adapter(reader)
        for name in ("send", "transmit", "write", "inject", "actuate"):
            self.assertFalse(hasattr(adapter, name), name)

    def test_config_rejects_invalid_stale_window(self):
        with self.assertRaises(ValueError):
            CanBodyAdapterConfig(stale_after_ms=0)


if __name__ == "__main__":
    unittest.main()

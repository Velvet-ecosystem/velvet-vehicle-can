import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestListenOnlyBackend(unittest.TestCase):
    def test_requests_passive_bus_and_exposes_no_send(self):
        bus = MagicMock()
        bus.recv.return_value = SimpleNamespace(
            timestamp=10.0,
            arbitration_id=0x321,
            data=b"\xaa",
        )
        can_module = MagicMock()
        can_module.BusState.PASSIVE = "passive"
        can_module.Bus.return_value = bus

        with patch.dict(sys.modules, {"can": can_module}):
            module = importlib.import_module("velvet_vehicle_can.listen_only_backend")
            reader = module.ListenOnlyPythonCanReader(module.ListenOnlyCanConfig())

        can_module.Bus.assert_called_once_with(
            channel="can0",
            interface="socketcan",
            receive_own_messages=False,
            state="passive",
        )
        self.assertEqual(reader.read_frame(), (10.0, 0x321, b"\xaa"))
        for name in ("send", "transmit", "write", "inject", "actuate"):
            self.assertFalse(hasattr(reader, name), name)


if __name__ == "__main__":
    unittest.main()

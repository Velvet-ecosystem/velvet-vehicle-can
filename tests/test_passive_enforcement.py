"""Synthetic iproute2 diagnostic fixtures; never opens a CAN interface."""
import copy
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from velvet_vehicle_can.socketcan_link import SocketCanLinkError, inspect_socketcan_link


def kernel_link():
    return {"ifindex": 2, "ifname": "can0", "flags": ["NOARP", "UP", "LOWER_UP", "ECHO"],
            "operstate": "UP", "linkinfo": {"info_kind": "can", "info_data": {
                "ctrlmode": ["LISTEN-ONLY"], "state": "ERROR-ACTIVE", "bittiming": {"bitrate": 500000}}}}


def result(value):
    return SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr="")


class PassiveEnforcementTests(unittest.TestCase):
    def test_structured_kernel_evidence(self):
        runner = Mock(return_value=result([kernel_link()]))
        evidence = inspect_socketcan_link("can0", runner=runner)
        self.assertEqual(evidence.bitrate, 500000)
        self.assertEqual(evidence.can_state, "ERROR-ACTIVE")
        self.assertIn("-json", runner.call_args[0][0])

    def test_unsafe_or_ambiguous_evidence_is_rejected(self):
        variants = [[], [kernel_link(), kernel_link()], [{}]]
        for path, value in [(('flags',), ['NOARP']), (('ifname',), 'can1'),
                            (('linkinfo','info_kind'), 'vcan'),
                            (('linkinfo','info_data','ctrlmode'), []),
                            (('linkinfo','info_data','ctrlmode'), ['LISTEN-ONLY','LOOPBACK']),
                            (('linkinfo','info_data','state'), 'BUS-OFF'),
                            (('linkinfo','info_data','bittiming','bitrate'), True)]:
            entry = kernel_link(); target = entry
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value; variants.append([entry])
        for value in variants:
            with self.subTest(value=value), self.assertRaises(SocketCanLinkError):
                inspect_socketcan_link('can0', runner=lambda *a, **kw: result(value))
        for text in ('', '{broken', '[{"ifname":"can0","ifname":"can1"}]'):
            with self.subTest(text=text), self.assertRaises(SocketCanLinkError):
                inspect_socketcan_link('can0', runner=lambda *a, **kw: SimpleNamespace(returncode=0,stdout=text,stderr=''))

    def test_missing_tool_refuses_reader_before_backend_construction(self):
        from velvet_vehicle_can.listen_only_backend import ListenOnlyCanConfig, ListenOnlyPythonCanReader
        backend = Mock()
        with patch.dict(sys.modules, {'can': backend}), patch(
            'velvet_vehicle_can.socketcan_link.subprocess.run', side_effect=FileNotFoundError('ip')):
            with self.assertRaises((SocketCanLinkError, RuntimeError)):
                ListenOnlyPythonCanReader(ListenOnlyCanConfig())
        backend.Bus.assert_not_called()

    def test_legacy_reader_has_no_unverified_or_public_bus_path(self):
        from velvet_vehicle_can.can_backend import PythonCanReader, SocketCanConfig
        backend = Mock()
        with patch.dict(sys.modules, {'can': backend}), patch(
            'velvet_vehicle_can.socketcan_link.subprocess.run', side_effect=FileNotFoundError('ip')):
            with self.assertRaises((SocketCanLinkError, RuntimeError)):
                PythonCanReader(SocketCanConfig())
        backend.Bus.assert_not_called(); backend.interface.Bus.assert_not_called()

    def test_non_socketcan_backends_cannot_skip_physical_verification(self):
        from velvet_vehicle_can.listen_only_backend import ListenOnlyCanConfig
        with self.assertRaises(ValueError): ListenOnlyCanConfig(bustype='virtual')


if __name__ == '__main__': unittest.main()

class OpenRaceTests(unittest.TestCase):
    def test_post_open_failure_closes_backend_without_receiving(self):
        from velvet_vehicle_can.listen_only_backend import ListenOnlyCanConfig, ListenOnlyPythonCanReader
        backend = Mock()
        with patch.dict(sys.modules, {'can': backend}), patch(
            'velvet_vehicle_can.listen_only_backend.inspect_socketcan_link',
            side_effect=[Mock(), SocketCanLinkError('mode changed')]):
            with self.assertRaises(SocketCanLinkError): ListenOnlyPythonCanReader(ListenOnlyCanConfig())
        backend.Bus.return_value.shutdown.assert_called_once()
        backend.Bus.return_value.recv.assert_not_called()

    def test_exact_independent_bitrate_is_checked(self):
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link('can0', runner=lambda *a, **kw: result([kernel_link()]), expected_bitrate=250000)

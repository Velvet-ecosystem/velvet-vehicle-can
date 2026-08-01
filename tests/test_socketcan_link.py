# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.evidence_topology import (
    EvidenceSourceKind,
    EvidenceSourceState,
    SignalSourceBinding,
    VehicleEvidenceTopology,
    VehicleGeneration,
)
from velvet_vehicle_can.socketcan_link import (
    SocketCanLinkError,
    build_live_can_preflight_receipt,
    inspect_socketcan_link,
)
from velvet_vehicle_can.vehicle_profile import VehicleProfile


class _Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class SocketCanLinkTests(unittest.TestCase):
    def test_verified_link_produces_bounded_evidence(self):
        output = """2: can0: <NOARP,UP,LOWER_UP> mtu 16 state UP mode DEFAULT
    link/can
    can state ERROR-ACTIVE (berr-counter tx 0 rx 0) restart-ms 0
      bitrate 500000 sample-point 0.875
      listen-only on
"""

        evidence = inspect_socketcan_link(
            "can0",
            runner=lambda *args, **kwargs: _Result(stdout=output),
            now=100.0,
        )

        self.assertEqual(evidence.bitrate, 500000)
        self.assertEqual(evidence.can_state, "ERROR-ACTIVE")
        self.assertTrue(evidence.listen_only)
        payload = evidence.to_dict()
        self.assertFalse(payload["transmission_attempted"])
        self.assertFalse(payload["grants_authority"])

    def test_missing_listen_only_fails_closed(self):
        output = """2: can0: <NOARP,UP,LOWER_UP> mtu 16 state UP
    can state ERROR-ACTIVE
      bitrate 500000
"""
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link(
                "can0",
                runner=lambda *args, **kwargs: _Result(stdout=output),
            )

    def test_down_link_and_missing_bitrate_fail_closed(self):
        down = """2: can0: <NOARP> mtu 16 state DOWN
    can state STOPPED
      bitrate 500000
      listen-only on
"""
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link(
                "can0",
                runner=lambda *args, **kwargs: _Result(stdout=down),
            )

        no_bitrate = """2: can0: <NOARP,UP> mtu 16 state UP
    can state ERROR-ACTIVE
      listen-only on
"""
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link(
                "can0",
                runner=lambda *args, **kwargs: _Result(stdout=no_bitrate),
            )

    def test_invalid_channel_and_command_failure_fail_closed(self):
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link("can0;shutdown")
        with self.assertRaises(SocketCanLinkError):
            inspect_socketcan_link(
                "can0",
                runner=lambda *args, **kwargs: _Result(
                    stderr="device missing", returncode=1
                ),
            )

    def test_preflight_receipt_includes_source_topology_without_claiming_frames(self):
        output = """2: can0: <NOARP,UP,LOWER_UP> mtu 16 state UP
    can state ERROR-ACTIVE
      bitrate 250000
      listen-only on
"""
        link = inspect_socketcan_link(
            "can0",
            runner=lambda *args, **kwargs: _Result(stdout=output),
            now=100.0,
        )
        profile = VehicleProfile(
            fingerprint_digest="western-star-candidate",
            evidence_topology=VehicleEvidenceTopology(
                generation=VehicleGeneration.MIXED,
                bindings=(
                    SignalSourceBinding(
                        canonical_signal="vehicle.ignition.state",
                        source_kind=EvidenceSourceKind.CAN,
                        source_ref="can:diagnostic-split",
                        transport="socketcan:can0",
                        state=EvidenceSourceState.DETECTED,
                    ),
                    SignalSourceBinding(
                        canonical_signal="vehicle.power.voltage",
                        source_kind=EvidenceSourceKind.HARDWIRED,
                        source_ref="adc:vehicle-voltage",
                        transport="isolated-analog-input",
                        state=EvidenceSourceState.VERIFIED,
                    ),
                ),
            ),
        )

        receipt = build_live_can_preflight_receipt(link, profile=profile)

        self.assertTrue(receipt["listen_only_verified"])
        self.assertFalse(receipt["frames_received"])
        self.assertFalse(receipt["signal_meaning_proven"])
        self.assertFalse(receipt["authority_granted"])
        self.assertEqual(
            receipt["profile"]["evidence_topology"]["generation"],
            "mixed",
        )


if __name__ == "__main__":
    unittest.main()

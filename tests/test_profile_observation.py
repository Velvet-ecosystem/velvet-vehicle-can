# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.can_observer import ObservedCanFrame
from velvet_vehicle_can.evidence_topology import (
    EvidenceSourceKind,
    EvidenceSourceState,
    SignalSourceBinding,
    VehicleEvidenceTopology,
    VehicleGeneration,
)
from velvet_vehicle_can.profile_observation import (
    decode_profile_observations,
    summarize_profile_observations,
)
from velvet_vehicle_can.vehicle_profile import SignalDef, SignalMap, VehicleProfile


class ProfileObservationTests(unittest.TestCase):
    def test_declared_can_source_caps_confidence_and_reports_cross_check(self):
        profile = VehicleProfile(
            fingerprint_digest="mixed-profile",
            signal_map=SignalMap(
                supply_voltage=SignalDef(
                    can_id=0x321,
                    start=0,
                    length=2,
                    endian="little",
                    scale=0.01,
                    confidence=0.95,
                )
            ),
            evidence_topology=VehicleEvidenceTopology(
                generation=VehicleGeneration.MIXED,
                bindings=(
                    SignalSourceBinding(
                        canonical_signal="vehicle.power.voltage",
                        source_kind=EvidenceSourceKind.CAN,
                        source_ref="can:body",
                        transport="socketcan:can0",
                        state=EvidenceSourceState.VERIFIED,
                        confidence_cap=0.8,
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
        frame = ObservedCanFrame(
            timestamp=10.0,
            can_id=0x321,
            data_hex="9005",
            dlc=2,
            extended=False,
        )

        observations = decode_profile_observations([frame], profile)

        self.assertEqual(len(observations), 1)
        item = observations[0]
        self.assertEqual(item.canonical_signal, "vehicle.power.voltage")
        self.assertAlmostEqual(item.value, 14.24)
        self.assertEqual(item.source_ref, "can:body")
        self.assertEqual(item.confidence, 0.8)
        self.assertTrue(item.topology_declared)
        self.assertTrue(item.independent_cross_check_available)
        self.assertFalse(item.to_dict()["grants_authority"])

    def test_missing_topology_is_labeled_implicit_detected_not_verified(self):
        profile = VehicleProfile(
            fingerprint_digest="modern-candidate",
            signal_map=SignalMap(
                ignition_state=SignalDef(
                    can_id=0x100,
                    start=0,
                    length=1,
                    confidence=0.6,
                )
            ),
        )
        frame = ObservedCanFrame(1.0, 0x100, "01", 1, False)

        observations = decode_profile_observations(
            [frame],
            profile,
            bus_source_ref="can:unknown-vehicle-bus",
        )

        item = observations[0]
        self.assertFalse(item.topology_declared)
        self.assertEqual(item.source_state, EvidenceSourceState.DETECTED)
        self.assertEqual(item.source_kind, EvidenceSourceKind.CAN)
        self.assertFalse(item.independent_cross_check_available)

    def test_summary_keeps_generation_and_authority_separate(self):
        profile = VehicleProfile(
            fingerprint_digest="legacy-profile",
            evidence_topology=VehicleEvidenceTopology(
                generation=VehicleGeneration.LEGACY
            ),
        )

        summary = summarize_profile_observations((), profile)

        self.assertEqual(summary["vehicle_generation"], "legacy")
        self.assertEqual(summary["observation_count"], 0)
        self.assertFalse(summary["grants_authority"])
        self.assertFalse(summary["actuation_performed"])


if __name__ == "__main__":
    unittest.main()

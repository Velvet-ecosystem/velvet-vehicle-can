# SPDX-License-Identifier: GPL-3.0-only

import json
import tempfile
import unittest
from pathlib import Path

from velvet_vehicle_can.evidence_topology import (
    EvidenceSourceKind,
    EvidenceSourceState,
    SignalSourceBinding,
    VehicleEvidenceTopology,
    VehicleGeneration,
)
from velvet_vehicle_can.vehicle_profile import (
    SignalDef,
    SignalMap,
    VehicleProfile,
    VehicleProfileStore,
)


class EvidenceTopologyTests(unittest.TestCase):
    def test_modern_can_profile_preserves_can_source(self):
        topology = VehicleEvidenceTopology(
            generation=VehicleGeneration.MODERN,
            bindings=(
                SignalSourceBinding(
                    canonical_signal="vehicle.ignition.state",
                    source_kind=EvidenceSourceKind.CAN,
                    source_ref="can:powertrain",
                    transport="socketcan:can0",
                    state=EvidenceSourceState.VERIFIED,
                    priority=10,
                    confidence_cap=0.95,
                ),
            ),
        )

        preferred = topology.preferred_source("vehicle.ignition.state")

        self.assertEqual(preferred.source_kind, EvidenceSourceKind.CAN)
        self.assertEqual(topology.generation, VehicleGeneration.MODERN)
        payload = topology.to_dict()
        self.assertFalse(payload["grants_authority"])
        self.assertFalse(payload["actuation_granted"])

    def test_legacy_profile_can_be_sparse_without_being_invalid(self):
        topology = VehicleEvidenceTopology(
            generation=VehicleGeneration.LEGACY,
            bindings=(
                SignalSourceBinding(
                    canonical_signal="vehicle.ignition.state",
                    source_kind=EvidenceSourceKind.HARDWIRED,
                    source_ref="gpio:ignition-isolated",
                    transport="isolated-digital-input",
                    state=EvidenceSourceState.VERIFIED,
                ),
            ),
        )

        coverage = topology.coverage(
            ("vehicle.ignition.state", "vehicle.power.voltage", "vehicle.speed")
        )

        self.assertEqual(coverage["verified"], ("vehicle.ignition.state",))
        self.assertIn("vehicle.speed", coverage["unavailable"])

    def test_mixed_profile_keeps_can_and_hardwired_cross_check(self):
        topology = VehicleEvidenceTopology(
            generation=VehicleGeneration.MIXED,
            bindings=(
                SignalSourceBinding(
                    canonical_signal="vehicle.power.voltage",
                    source_kind=EvidenceSourceKind.CAN,
                    source_ref="can:body",
                    transport="socketcan:can0",
                    state=EvidenceSourceState.VERIFIED,
                    priority=20,
                ),
                SignalSourceBinding(
                    canonical_signal="vehicle.power.voltage",
                    source_kind=EvidenceSourceKind.HARDWIRED,
                    source_ref="adc:vehicle-voltage",
                    transport="isolated-analog-input",
                    state=EvidenceSourceState.VERIFIED,
                    priority=10,
                ),
            ),
        )

        sources = topology.sources_for("vehicle.power.voltage")

        self.assertEqual(sources[0].source_ref, "adc:vehicle-voltage")
        self.assertTrue(
            topology.has_independent_cross_check("vehicle.power.voltage")
        )

    def test_same_source_kind_does_not_claim_independent_cross_check(self):
        topology = VehicleEvidenceTopology(
            bindings=(
                SignalSourceBinding(
                    canonical_signal="vehicle.speed",
                    source_kind=EvidenceSourceKind.CAN,
                    source_ref="can:front-wheel",
                    transport="socketcan:can0",
                    state=EvidenceSourceState.VERIFIED,
                ),
                SignalSourceBinding(
                    canonical_signal="vehicle.speed",
                    source_kind=EvidenceSourceKind.CAN,
                    source_ref="can:rear-wheel",
                    transport="socketcan:can0",
                    state=EvidenceSourceState.VERIFIED,
                ),
            )
        )

        self.assertFalse(topology.has_independent_cross_check("vehicle.speed"))

    def test_unknown_signal_and_duplicate_binding_fail_closed(self):
        with self.assertRaises(KeyError):
            SignalSourceBinding(
                canonical_signal="vehicle.teleport.state",
                source_kind=EvidenceSourceKind.SPECIALIZED,
                source_ref="retrofit:teleport",
                transport="fiction",
            )

        binding = SignalSourceBinding(
            canonical_signal="vehicle.speed",
            source_kind=EvidenceSourceKind.SPECIALIZED,
            source_ref="retrofit:wheel-sensor",
            transport="uart",
        )
        with self.assertRaises(ValueError):
            VehicleEvidenceTopology(bindings=(binding, binding))

    def test_profile_round_trip_preserves_topology_and_new_signals(self):
        topology = VehicleEvidenceTopology(
            generation=VehicleGeneration.MIXED,
            bindings=(
                SignalSourceBinding(
                    canonical_signal="vehicle.power.voltage",
                    source_kind=EvidenceSourceKind.CAN,
                    source_ref="can:body",
                    transport="socketcan:can0",
                    state=EvidenceSourceState.DETECTED,
                    confidence_cap=0.8,
                ),
            ),
        )
        profile = VehicleProfile(
            fingerprint_digest="abc123",
            signal_map=SignalMap(
                supply_voltage=SignalDef(
                    can_id=0x321,
                    start=0,
                    length=2,
                    scale=0.01,
                    confidence=0.8,
                ),
                engine_running=SignalDef(
                    can_id=0x322,
                    start=0,
                    length=1,
                    confidence=0.7,
                ),
            ),
            evidence_topology=topology,
        )

        with tempfile.TemporaryDirectory() as directory:
            store = VehicleProfileStore(directory)
            store.save(profile)
            loaded = store.load("abc123")

        self.assertEqual(loaded.evidence_topology.generation, VehicleGeneration.MIXED)
        self.assertIsNotNone(loaded.signal_map.supply_voltage)
        self.assertIsNotNone(loaded.signal_map.engine_running)
        self.assertEqual(
            loaded.evidence_topology.bindings[0].source_ref,
            "can:body",
        )

    def test_old_profile_without_topology_loads_as_unknown(self):
        document = {
            "fingerprint_digest": "legacy-profile",
            "signal_map": {},
            "stage": 0,
            "validation_score": 0.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-profile.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            loaded = VehicleProfileStore(directory).load_path(path)

        self.assertEqual(
            loaded.evidence_topology.generation,
            VehicleGeneration.UNKNOWN,
        )
        self.assertEqual(loaded.evidence_topology.bindings, ())


if __name__ == "__main__":
    unittest.main()

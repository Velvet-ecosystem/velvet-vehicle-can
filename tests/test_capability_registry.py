# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.capability_registry import (
    VEHICLE_CAPABILITY_CATALOG,
    CapabilityDefinition,
    CapabilityState,
    VehicleCapability,
    can_transition_capability,
    get_capability_definition,
    transition_capability,
    validate_capability_catalog,
)


class TestCapabilityRegistry(unittest.TestCase):
    def test_catalog_lookup(self):
        steering = get_capability_definition("vehicle.control.steering")
        self.assertIsNotNone(steering)
        self.assertTrue(steering.control_related)
        self.assertTrue(steering.safety_critical)

    def test_capability_presence_never_grants_authority(self):
        capability = VehicleCapability(
            "vehicle.control.steering",
            CapabilityState.ENABLED,
            evidence="bench-qualified EPS interface",
            source="tiburon_v0",
        )
        payload = capability.to_dict()
        self.assertFalse(payload["grants_permission"])
        self.assertFalse(payload["grants_authority"])
        self.assertFalse(payload["actuation_granted"])

    def test_state_advances_one_step_only(self):
        self.assertTrue(can_transition_capability(CapabilityState.DETECTED, CapabilityState.INSTALLED))
        self.assertTrue(can_transition_capability(CapabilityState.VERIFIED, CapabilityState.VERIFIED))
        self.assertFalse(can_transition_capability(CapabilityState.DETECTED, CapabilityState.QUALIFIED))
        self.assertFalse(can_transition_capability(CapabilityState.QUALIFIED, CapabilityState.VERIFIED))

    def test_transition_preserves_evidence_unless_replaced(self):
        original = VehicleCapability(
            "vehicle.observe.can",
            CapabilityState.DETECTED,
            evidence="interface enumerated",
            source="founder",
        )
        updated = transition_capability(original, CapabilityState.INSTALLED)
        self.assertEqual(updated.evidence, "interface enumerated")
        self.assertEqual(updated.source, "founder")

    def test_unknown_capability_fails_closed(self):
        unknown = VehicleCapability("vehicle.control.teleport", CapabilityState.ABSENT)
        with self.assertRaises(KeyError):
            transition_capability(unknown, CapabilityState.DETECTED)

    def test_duplicate_ids_are_rejected(self):
        duplicate = CapabilityDefinition("vehicle.observe.can", "duplicate")
        with self.assertRaises(ValueError):
            validate_capability_catalog((VEHICLE_CAPABILITY_CATALOG[0], duplicate))

    def test_control_capability_namespace_is_enforced(self):
        invalid = CapabilityDefinition("vehicle.observe.fake_control", "bad", control_related=True)
        with self.assertRaises(ValueError):
            validate_capability_catalog((invalid,))


if __name__ == "__main__":
    unittest.main()

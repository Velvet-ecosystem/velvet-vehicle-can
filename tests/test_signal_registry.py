# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.signal_registry import (
    CANONICAL_SIGNAL_CATALOG,
    SignalCatalogEntry,
    SignalLifecycle,
    can_transition_signal,
    canonical_name_for,
    get_signal_by_name,
    get_signal_by_profile_field,
    validate_catalog,
)


class TestSignalRegistry(unittest.TestCase):
    def test_profile_fields_resolve_to_canonical_names(self):
        self.assertEqual(canonical_name_for("wheel_speed"), "vehicle.speed")
        self.assertEqual(canonical_name_for("engine_rpm"), "vehicle.engine.rpm")

    def test_lookup_works_in_both_directions(self):
        by_name = get_signal_by_name("vehicle.steering.angle")
        by_field = get_signal_by_profile_field("steering_angle")
        self.assertIsNotNone(by_name)
        self.assertEqual(by_name, by_field)
        self.assertTrue(by_name.safety_relevant)

    def test_unknown_profile_field_fails_closed(self):
        with self.assertRaises(KeyError):
            canonical_name_for("mystery_signal")

    def test_lifecycle_advances_one_step_only(self):
        self.assertTrue(can_transition_signal(SignalLifecycle.CANDIDATE, SignalLifecycle.OBSERVED))
        self.assertTrue(can_transition_signal(SignalLifecycle.OBSERVED, SignalLifecycle.OBSERVED))
        self.assertFalse(can_transition_signal(SignalLifecycle.CANDIDATE, SignalLifecycle.VALIDATED))
        self.assertFalse(can_transition_signal(SignalLifecycle.VALIDATED, SignalLifecycle.CORRELATED))

    def test_catalog_is_unique_and_read_only(self):
        validate_catalog(CANONICAL_SIGNAL_CATALOG)
        payload = CANONICAL_SIGNAL_CATALOG[0].to_dict()
        self.assertEqual(payload["authority"], "none")
        self.assertTrue(payload["read_only"])

    def test_duplicate_names_are_rejected(self):
        entry = SignalCatalogEntry("vehicle.speed", "speed_copy", "duplicate")
        with self.assertRaises(ValueError):
            validate_catalog((CANONICAL_SIGNAL_CATALOG[0], entry))


if __name__ == "__main__":
    unittest.main()

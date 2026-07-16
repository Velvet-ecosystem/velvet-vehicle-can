# SPDX-License-Identifier: GPL-3.0-only

import unittest

from velvet_vehicle_can.capability_registry import CapabilityState
from velvet_vehicle_can.capability_tokens import (
    CapabilityToken,
    TokenValidationContext,
    validate_capability_token,
)


class TestCapabilityTokens(unittest.TestCase):
    def setUp(self):
        self.token = CapabilityToken(
            token_id="token-123",
            capability_id="vehicle.control.steering",
            subject="charlotte",
            issuer="court",
            purpose="emergency-pull-over",
            body_id="tiburon_v0",
            issued_at=100.0,
            expires_at=110.0,
            receipt_context="receipt-456",
        )
        self.context = TokenValidationContext(
            now=105.0,
            expected_subject="charlotte",
            expected_body_id="tiburon_v0",
            capability_state=CapabilityState.ENABLED,
            integrity_verified=True,
            safety_gate_open=True,
            receipt_available=True,
        )

    def test_valid_token_is_authorization_evidence_only(self):
        result = validate_capability_token(self.token, self.context)
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "authorization-evidence-valid")
        self.assertFalse(result.to_dict()["grants_execution"])
        self.assertFalse(result.to_dict()["actuation_performed"])
        self.assertFalse(self.token.to_dict()["executes_action"])

    def test_expired_token_fails_closed(self):
        context = TokenValidationContext(**{**self.context.__dict__, "now": 110.0})
        result = validate_capability_token(self.token, context)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "expired")

    def test_wrong_subject_or_body_fails_closed(self):
        subject_context = TokenValidationContext(
            **{**self.context.__dict__, "expected_subject": "ruby"}
        )
        body_context = TokenValidationContext(
            **{**self.context.__dict__, "expected_body_id": "dakota_v0"}
        )
        self.assertEqual(
            validate_capability_token(self.token, subject_context).reason,
            "subject-mismatch",
        )
        self.assertEqual(
            validate_capability_token(self.token, body_context).reason,
            "body-mismatch",
        )

    def test_integrity_receipt_and_gate_are_required(self):
        cases = (
            ("integrity_verified", False, "integrity-unverified"),
            ("receipt_available", False, "receipt-context-unavailable"),
            ("safety_gate_open", False, "safety-gate-closed"),
        )
        for field, value, reason in cases:
            context = TokenValidationContext(**{**self.context.__dict__, field: value})
            self.assertEqual(validate_capability_token(self.token, context).reason, reason)

    def test_driver_override_wins(self):
        context = TokenValidationContext(
            **{**self.context.__dict__, "driver_override_active": True}
        )
        result = validate_capability_token(self.token, context)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "driver-override-active")

    def test_capability_must_be_enabled(self):
        context = TokenValidationContext(
            **{**self.context.__dict__, "capability_state": CapabilityState.QUALIFIED}
        )
        result = validate_capability_token(self.token, context)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "capability-not-enabled")

    def test_lifetime_is_bounded(self):
        long_token = CapabilityToken(
            **{**self.token.__dict__, "expires_at": 200.0}
        )
        result = validate_capability_token(long_token, self.context)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "lifetime-exceeds-limit")

    def test_unregistered_capability_fails_closed(self):
        token = CapabilityToken(
            **{**self.token.__dict__, "capability_id": "vehicle.control.teleport"}
        )
        result = validate_capability_token(token, self.context)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "capability-unregistered")


if __name__ == "__main__":
    unittest.main()

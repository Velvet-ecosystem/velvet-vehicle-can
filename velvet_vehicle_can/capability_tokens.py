# SPDX-License-Identifier: GPL-3.0-only
"""Fail-closed capability token envelopes for future Court integration.

This module defines and validates authorization evidence. It does not issue
trusted tokens, perform cryptographic verification, or execute vehicle actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .capability_registry import CapabilityState, get_capability_definition


@dataclass(frozen=True)
class CapabilityToken:
    token_id: str
    capability_id: str
    subject: str
    issuer: str
    purpose: str
    body_id: str
    issued_at: float
    expires_at: float
    receipt_context: str
    driver_override_required: bool = True
    safety_gate_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "velvet.vehicle.capability-token.v1",
            "token_id": self.token_id,
            "capability_id": self.capability_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "purpose": self.purpose,
            "body_id": self.body_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "receipt_context": self.receipt_context,
            "driver_override_required": self.driver_override_required,
            "safety_gate_required": self.safety_gate_required,
            "executes_action": False,
            "actuation_performed": False,
        }


@dataclass(frozen=True)
class TokenValidationContext:
    now: float
    expected_subject: str
    expected_body_id: str
    capability_state: CapabilityState
    integrity_verified: bool
    driver_override_active: bool = False
    safety_gate_open: bool = False
    receipt_available: bool = False
    maximum_lifetime_s: float = 60.0


@dataclass(frozen=True)
class TokenValidationResult:
    valid: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "grants_execution": False,
            "actuation_performed": False,
        }


def validate_capability_token(
    token: CapabilityToken,
    context: TokenValidationContext,
) -> TokenValidationResult:
    """Validate authorization evidence without executing or granting an action."""

    if get_capability_definition(token.capability_id) is None:
        return TokenValidationResult(False, "capability-unregistered")
    if not token.token_id.strip():
        return TokenValidationResult(False, "token-id-missing")
    if not token.issuer.strip():
        return TokenValidationResult(False, "issuer-missing")
    if not token.purpose.strip():
        return TokenValidationResult(False, "purpose-missing")
    if not token.receipt_context.strip() or not context.receipt_available:
        return TokenValidationResult(False, "receipt-context-unavailable")
    if not context.integrity_verified:
        return TokenValidationResult(False, "integrity-unverified")
    if token.subject != context.expected_subject:
        return TokenValidationResult(False, "subject-mismatch")
    if token.body_id != context.expected_body_id:
        return TokenValidationResult(False, "body-mismatch")
    if token.expires_at <= token.issued_at:
        return TokenValidationResult(False, "invalid-time-window")
    if token.expires_at - token.issued_at > context.maximum_lifetime_s:
        return TokenValidationResult(False, "lifetime-exceeds-limit")
    if context.now < token.issued_at:
        return TokenValidationResult(False, "not-yet-valid")
    if context.now >= token.expires_at:
        return TokenValidationResult(False, "expired")
    if context.capability_state is not CapabilityState.ENABLED:
        return TokenValidationResult(False, "capability-not-enabled")
    if token.driver_override_required and context.driver_override_active:
        return TokenValidationResult(False, "driver-override-active")
    if token.safety_gate_required and not context.safety_gate_open:
        return TokenValidationResult(False, "safety-gate-closed")

    return TokenValidationResult(True, "authorization-evidence-valid")

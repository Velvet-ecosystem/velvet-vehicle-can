# Vehicle Capability Token Contract

## Purpose

A vehicle capability token is short-lived authorization evidence for one subject, one vehicle body, one capability, and one stated purpose.

It does not execute an action. It does not replace Court, safety gates, executors, driver override handling, or receipts.

## Required fields

A token carries:

- unique token ID
- registered capability ID
- subject or organ identity
- issuer identity
- purpose
- vehicle body ID
- issue and expiry times
- receipt context
- driver-override requirement
- safety-gate requirement

## Validation inputs

The validator also requires trusted local context:

- current time
- expected subject
- expected body identity
- current capability state
- independently verified token integrity
- driver override state
- safety-gate state
- receipt availability
- maximum accepted lifetime

The token cannot mark its own integrity as verified. That decision belongs to Court or another trusted local verifier.

## Fail-closed reasons

Validation rejects tokens when:

- the capability is not registered
- token ID, issuer, purpose, or receipt context is missing
- integrity has not been independently verified
- subject or body identity does not match
- the time window is invalid, premature, expired, or too long
- the body capability is not enabled
- driver override is active
- the required safety gate is closed
- receipt context is unavailable

## Example

```json
{
  "schema": "velvet.vehicle.capability-token.v1",
  "token_id": "token-123",
  "capability_id": "vehicle.control.steering",
  "subject": "charlotte",
  "issuer": "court",
  "purpose": "emergency-pull-over",
  "body_id": "tiburon_v0",
  "issued_at": 100.0,
  "expires_at": 110.0,
  "receipt_context": "receipt-456",
  "driver_override_required": true,
  "safety_gate_required": true,
  "executes_action": false,
  "actuation_performed": false
}
```

## Required flow

```text
request
  -> Court and policy decision
  -> token issuance outside this repository
  -> integrity verification
  -> subject and body binding
  -> capability-state check
  -> driver-override check
  -> safety-gate check
  -> receipt-context check
  -> bounded executor decision
  -> receipt
```

This repository defines the token envelope and fail-closed validation contract only. It does not issue cryptographically trusted tokens and contains no vehicle-control executor.

## Public rule

Capabilities describe what the body has.

Tokens carry narrow authorization evidence.

Gates judge present safety.

Executors remain separate.

Driver override always wins.

Receipts remember.

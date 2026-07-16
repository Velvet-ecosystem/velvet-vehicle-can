# CAN Observation Event Contract

## Purpose

`velvet-vehicle-can` converts trusted, decoded CAN observations into a stable event envelope for Velvet runtime, receipts, interface, and organ consumers.

The envelope reports what was observed. It never grants permission, requests an action, or represents vehicle authority.

## Event identity

Single observation:

```text
velvet.vehicle.can.signal.observed
```

Schema:

```text
velvet.can.observation.v1
```

## Required safety claims

Every event declares:

- `mode: read-only`
- `status: observation-only`
- `authority: none`
- `actuation_granted: false`
- `actuation_performed: false`

Consumers must not reinterpret confidence as authority. Confidence describes trust in the learned decoding only.

## Example

```json
{
  "schema": "velvet.can.observation.v1",
  "event": "velvet.vehicle.can.signal.observed",
  "source": "velvet-vehicle-can",
  "mode": "read-only",
  "status": "observation-only",
  "observed_at": 12.5,
  "bus": "obd_can",
  "signal": "wheel_speed",
  "value": 42.5,
  "raw_value": 425,
  "confidence": 0.91,
  "can_id": 512,
  "can_id_hex": "0x200",
  "profile_digest": "example-profile-digest",
  "authority": "none",
  "actuation_granted": false,
  "actuation_performed": false
}
```

## Consumer rules

Runtime may route the event. Receipts may record it. The interface may display it. Ruby may correlate it with diagnostics. Charlotte and Temperance may use it only as one observation among their independently gated inputs.

No consumer may turn this event directly into CAN transmission, actuator movement, or a vehicle-control command.

Any future control path must remain separate and require explicit registration, Court authorization, safety qualification, executor isolation, driver override handling, and receipts.

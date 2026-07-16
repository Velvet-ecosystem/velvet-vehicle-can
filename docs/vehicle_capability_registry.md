# Vehicle Capability Registry

## Purpose

The vehicle capability registry records what hardware and observation surfaces a vehicle body has.

It does not grant permission, authority, or control.

A capability answers:

> What exists on this body, and how far has that hardware been verified?

It does not answer:

> May Velvet use it right now?

Permission remains with Court, policy, capability tokens, safety gates, executors, driver override handling, and receipts.

## Capability states

```text
absent
  -> detected
  -> installed
  -> verified
  -> qualified
  -> enabled
```

A helper may hold the current state or advance exactly one step. Skipping stages and demotion require explicit external review.

State meanings:

- `absent`: not present on the body
- `detected`: evidence suggests the capability exists
- `installed`: hardware is physically installed or connected
- `verified`: identity, wiring, and expected behaviour were checked
- `qualified`: applicable bench or vehicle safety qualification passed
- `enabled`: available to an authorized executor under current policy

Even `enabled` does not grant permission or authority by itself.

## Canonical capability IDs

Observation examples:

- `vehicle.observe.can`
- `vehicle.observe.obd2`
- `vehicle.observe.gnss`
- `vehicle.observe.camera.outward`
- `vehicle.observe.camera.inward`
- `vehicle.observe.cabin`

Control-hardware examples:

- `vehicle.control.steering`
- `vehicle.control.brake`
- `vehicle.control.throttle`
- `vehicle.control.clutch`
- `vehicle.control.shifter`
- `vehicle.control.door.lock`
- `vehicle.control.window`
- `vehicle.control.lighting`
- `vehicle.control.hvac`

Control-related entries describe hardware surfaces only. They are not commands and cannot authorize actuation.

## Tiburon example

A present-day Tiburon body record may include:

```text
vehicle.observe.can              enabled
vehicle.observe.obd2             enabled
vehicle.observe.gnss             installed
vehicle.observe.camera.outward   installed
vehicle.observe.cabin            detected
vehicle.control.steering         absent
vehicle.control.brake            absent
vehicle.control.throttle         absent
vehicle.control.clutch           absent
vehicle.control.shifter          absent
```

As retrofit hardware is added, each capability advances through evidence-backed stages instead of appearing suddenly as usable control.

## Required separation

```text
Capability registry: hardware exists
Court and policy: request is authorized
Safety gate: present conditions permit it
Executor: performs the bounded action
Receipt: records what occurred
```

Forbidden interpretation:

```text
hardware installed -> Velvet may control it
```

## Public rule

Capabilities describe the body.

Policies describe permission.

Gates describe present safety.

Executors perform actions.

Receipts remember.

# Public Ghost CAN Demo

The ghost CAN demo is the first safe public loop for `velvet-vehicle-can`. It proves the repo can observe and decode vehicle-shaped telemetry without opening a hardware bus, sending a CAN frame, or touching any actuator.

## Purpose

```text
synthetic CAN frame
  -> FakeCanReader
  -> ReceiveOnlyCanObserver
  -> learned-profile style decoder
  -> vehicle.can.ghost_observation event
  -> receipt/runtime/UI in the public ghost system
```

## Run it

```bash
python -m velvet_vehicle_can.ghost_can_demo --pretty
python -m velvet_vehicle_can.ghost_can_demo --fixture examples/fixtures/tiburon_ghost_frames.jsonl --pretty
velvet-ghost-can --pretty
```

## Safety boundary

The demo always reports `read_only: true`, `hardware_bus_opened: false`, `actuation_granted: false`, and `actuation_performed: false`.

The event type is `vehicle.can.ghost_observation`. It is observation-only and must never be treated as authority.

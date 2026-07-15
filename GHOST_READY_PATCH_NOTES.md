# Ghost-Ready Patch Notes

This patch prepares `velvet-vehicle-can` to serve the public Velvet ghost system without exposing vehicle-control behavior.

## Added

- `velvet_vehicle_can/ghost_can_demo.py`
- `examples/ghost_can_demo.py`
- `examples/fixtures/tiburon_ghost_frames.jsonl`
- `docs/ghost_can_demo.md`
- `docs/public_runtime_adapter_contract.md`
- `tests/test_ghost_can_demo.py`
- Console entry point: `velvet-ghost-can`

## Updated

- `SignalMap` includes additional read-only ghost/runtime observations: `engine_rpm`, `ignition_state`, `driver_door`, and `o2_fault`.
- `VehicleProfileStore` reconstructs those additional signal fields.

## Verified

```text
python -m unittest discover -s tests -v
Ran 16 tests
OK
```

## Safety status

The public ghost demo does not open a hardware CAN bus and does not provide any transmit, send, inject, write, or actuation surface.

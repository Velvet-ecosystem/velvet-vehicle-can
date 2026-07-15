# Public Runtime Adapter Contract

`velvet-vehicle-can` stays focused on CAN observation. The public runtime owns command routing, receipts, UI updates, and cross-module orchestration.

The ghost demo emits `vehicle.can.ghost_observation` with required safety fields:

```json
{
  "read_only": true,
  "hardware_bus_opened": false,
  "actuation_granted": false,
  "actuation_performed": false
}
```

This repository may provide receive-only normalization, synthetic ghost frames, learned-profile decoding, observation summaries, and passive fingerprint/profile learning.

It must not provide CAN transmit helpers, actuator executors, pedal/steering/throttle control, emergency maneuver logic, private vehicle pinouts, or deployment secrets.

# CAN Signal Registry

## Purpose

This registry gives Velvet one vehicle-independent vocabulary for CAN observations.

Vehicle adapters and learned profiles may use local fields such as `wheel_speed`. Runtime, receipts, interfaces, and organs receive canonical names such as `vehicle.speed`.

The registry does not grant authority. Every entry is read-only by default.

## Lifecycle

Signals advance conservatively:

```text
unknown
  -> candidate
  -> observed
  -> correlated
  -> validated
  -> qualified
```

A helper may hold the current state or advance exactly one step. Skipping stages, demotion, and qualification require an explicit external review and receipt flow.

`qualified` means the observation has passed the applicable validation process. It does not mean the signal may command the vehicle.

## Canonical catalog

| Canonical name | Profile field | Meaning | Safety relevant |
| --- | --- | --- | --- |
| `vehicle.speed` | `wheel_speed` | Vehicle road speed | yes |
| `vehicle.engine.rpm` | `engine_rpm` | Engine rotational speed | no |
| `vehicle.steering.angle` | `steering_angle` | Measured steering angle | yes |
| `vehicle.steering.request` | `steering_request` | Observed steering request | yes |
| `vehicle.brake.request` | `brake_request` | Observed brake request | yes |
| `vehicle.throttle.request` | `throttle_request` | Observed throttle request | yes |
| `vehicle.gear.current` | `gear` | Current gear or selector state | no |
| `vehicle.ignition.state` | `ignition_state` | Ignition or run state | no |
| `vehicle.door.driver.state` | `driver_door` | Driver-door state | no |
| `vehicle.diagnostics.o2_fault` | `o2_fault` | Oxygen-sensor fault state | no |
| `vehicle.cruise.state` | `cruise_state` | Cruise-control state | yes |

## Naming rules

Canonical names:

- begin with `vehicle.`
- describe observations, not commands
- remain stable across vehicle makes and models
- preserve the adapter/profile field separately for provenance
- require a registry entry before runtime event publication

## Adapter example

```text
Tiburon profile: wheel_speed
        -> vehicle.speed

Future Toyota profile: wheel_speed
        -> vehicle.speed
```

Everything above the adapter consumes `vehicle.speed`.

## Safety rule

Unknown profile fields fail closed when converted into runtime CAN observation events. They must first be reviewed and added to the registry.

Canonical naming standardizes meaning. It does not authorize transmission, control, or actuation.

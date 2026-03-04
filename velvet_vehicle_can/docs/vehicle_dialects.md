# Vehicle Dialects (CAN Language Learning)

Modern vehicles share the same physical nervous system (CAN), but not the same language.
Each OEM (and often each model year/trim) encodes steering, braking, throttle, and status
signals differently.

Velvet does not rely on a static compatibility list.
Velvet learns a vehicle’s CAN dialect locally, stores it as a per-vehicle profile, and
progressively unlocks capability through confidence-gated validation.

## Goals

- Learn vehicle control & status signals by passive observation + correlation.
- Store learned profiles locally (offline-first).
- Support multiple vehicles without a cloud database.
- Minimize risk: read-only first, shadow-prediction, then limited injection.

## Non-goals

- No reflashing ECUs.
- No bypassing safety-critical OEM systems.
- No “full control” without validation, kill paths, and driver authority.

## Key Concepts

### VehicleProfile
A local-first record that binds:
- Vehicle identity (VIN hash where available, plus CAN fingerprint)
- Learned SignalMap
- Confidence per signal / capability
- Safety limits and unlock state
- Validation history

### CAN Fingerprint
A stable signature derived from:
- Arbitration IDs present on the bus
- Message rates (Hz) per ID
- Byte-level counters / checksums patterns
- Optional OBD details (VIN, model, ECU list)

Fingerprinting allows Velvet to:
- Recognize the same vehicle again
- Detect major bus changes (module replacement, trim change)
- Avoid applying the wrong SignalMap

### SignalMap
A structured mapping of “what message/bytes mean what”.
Examples:
- wheel speed
- steering angle
- steering torque request
- brake request / decel request
- throttle request
- gear / cruise state
- blinkers / wipers (optional)

Each mapping includes:
- CAN ID
- byte slice (start, length)
- endianness, signedness
- scaling/offset
- counter field definition (if present)
- checksum definition (if present)
- confidence score

### Confidence Gating
Every learned signal has a confidence score.
Capability unlocks are staged:
- Stage 0: Passive sniff only
- Stage 1: Status decode (speed, steering angle, etc.)
- Stage 2: Shadow prediction (no injection)
- Stage 3: Limited injection (low authority, strict bounds)
- Stage 4: Extended injection (still bounded, driver override always wins)

## Safety Rules (Hard)

- Default is READ-ONLY.
- Injection is disabled unless:
  1) vehicle is correctly identified (profile match),
  2) required signals reach confidence threshold,
  3) validation checks pass,
  4) kill-switch is available and tested.
- Any anomaly drops to safe mode immediately:
  - checksum mismatch
  - counter discontinuity
  - unexpected ECU responses
  - sensor disagreement
  - driver override detected

## Data Sources for Learning

- CAN frames (timestamped)
- Driver inputs (steering wheel angle/torque, pedal positions where available)
- IMU (accel/yaw) if present
- Wheel speeds (CAN) and/or GPS speed (sanity check)
- Seat/presence signals for “driver in control” assertions

## Storage & Privacy

- Profiles are stored locally (offline-first).
- VIN is stored as a hash by default (privacy).
- Raw logs can be optionally retained for debugging; otherwise store only learned maps.

## Integration Points

- `can_fingerprint.py` generates/updates fingerprint
- `can_dialect_learner.py` produces a SignalMap from logs
- `vehicle_profile.py` persists and loads profiles
- MemoryCore records learning/validation events as MemoryEvent entries

# CAN Learning Pipeline (New Vehicle Onboarding)

This document describes how Velvet learns a new vehicle’s CAN dialect safely.

## Stage 0 — Passive Sniff

**Goal:** Observe without affecting the bus.

Actions:
- Listen to all frames on available buses (OBD-CAN, camera CAN, etc. if accessible).
- Build a baseline: IDs present, frequencies, byte variability.

Outputs:
- Initial CAN fingerprint
- Raw observation log (optional retention)

Exit criteria:
- Stable fingerprint (no major drift for N minutes)
- Bus load acceptable

## Stage 1 — Vehicle Identification

**Goal:** Bind observations to a consistent identity.

Actions:
- Attempt OBD read (VIN, ECU list) if available.
- Derive fingerprint from CAN traffic patterns.
- Compare to existing profiles.

Outputs:
- `VehicleIdentity` (vin_hash + fingerprint)
- Profile match score

Exit criteria:
- Either: matched known profile, or created new profile shell.

## Stage 2 — Signal Discovery via Correlation

**Goal:** Find candidate signals by relating driver actions and motion to frame changes.

Method:
- Annotate segments where driver performs isolated actions:
  - steady cruise (constant throttle)
  - gentle brake events
  - left/right steering sweeps
- Compute candidate IDs/bytes that correlate with:
  - steering changes
  - longitudinal accel changes
  - brake application
  - wheel speed changes

Common patterns:
- Wheel speeds: 4 similar channels changing with motion
- Steering angle/torque: changes with wheel input, higher frequency
- Pedal/brake request: step-like changes, may include counters/checksums

Outputs:
- Candidate mappings with confidence estimates

Exit criteria:
- At minimum: reliable speed + steering angle (or equivalent)
- Prefer: brake and throttle status channels (even if not requests)

## Stage 3 — Counter/Checksum Modeling

**Goal:** Determine frame integrity rules for candidate control messages.

Actions:
- Detect counters: byte/bit fields incrementing modulo N
- Detect checksums/CRC: validate by brute force of known patterns
- Record rules as part of mapping

Outputs:
- `IntegrityRule` per message (counter field, checksum type)

Exit criteria:
- Control-signal candidates must have integrity modeled before any injection.

## Stage 4 — Shadow Prediction (No Injection)

**Goal:** Prove decoding correctness without touching the car.

Actions:
- Run the learned map live and predict near-term outcomes:
  - If steering angle increases left, yaw should reflect it
  - If brake status increases, decel should follow
- Cross-check sensor fusion (CAN vs IMU vs GPS).

Outputs:
- Validation score time series
- Confidence updates

Exit criteria:
- Sustained high validation score over time and scenarios

## Stage 5 — Limited Injection (Low Authority)

**Goal:** Apply minimal commands within strict bounds.

Rules:
- Only when driver is attentive + explicitly armed
- Only small steering/accel deltas
- Immediate drop on driver override
- Rate limiting and envelope constraints

Examples:
- tiny lane-centering nudges
- mild ACC adjustments (if safe)

Outputs:
- Injection audit log
- Updated confidence

Exit criteria:
- No anomalies over N sessions
- Driver override works instantly every time

## Stage 6 — Extended Capability (Still Bounded)

**Goal:** Expand control envelope gradually.

Actions:
- Increase allowed authority slowly
- Add more scenarios and validate
- Record “capability unlocks” as a function of confidence + validation history

Hard rule:
- If anything smells wrong, revert to Stage 0/1 and require re-validation.

## Kill Paths & Failsafes (Always Required)

- Physical kill switch (preferred)
- Software emergency stop bound to:
  - brake pedal press
  - steering wheel torque override
  - critical sensor disagreement
  - checksum/counter mismatch
- Watchdog: if Velvet stops responding, injection stops

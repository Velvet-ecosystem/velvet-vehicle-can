# Vehicle network and gateway contracts

Date: 2026-08-29
Status: contract draft
Owner repo: velvet-vehicle-can

## Purpose

Velvet should not let Queen wrestle raw vehicle buses directly. Vehicle-facing networks need deterministic boundaries, timing ownership, health counters, replay hooks, and clear rules for future bus evolution.

## 1. Deterministic Vehicle Gateway Contract

Canonical boundary:

```text
vehicle buses -> deterministic gateway -> Event Protocol -> Queen
```

Gateway responsibilities:

- own physical CAN, CAN-FD, LIN, and future Ethernet interfaces
- preserve bus timing
- filter unsafe or irrelevant traffic
- normalize observations
- expose health and error counters
- provide replay hooks
- isolate noisy or compromised buses
- emit receipts for state transitions

Suggested descriptor:

```yaml
gateway_id: string
vehicle_target: tiburon | western_star | dakota | bench | generic
physical_buses: [string]
read_only: boolean
write_allowed: boolean
write_authority_source: court_only | disabled | maintenance_only
filter_profile: string
normalization_profile: string
replay_supported: boolean
fault_injection_supported: boolean
health_counter_set: string
receipt_types: [string]
```

Rule: raw vehicle bus access is adapter work. Queen receives normalized, receipted vehicle truth.

## 2. Network Evolution Matrix

Velvet does not need one universal bus. It needs the right road for each traffic type.

Network types to track:

- CAN
- CAN-FD
- CAN XL
- LIN
- 100BASE-T1
- 10BASE-T1S
- asymmetric camera Ethernet
- ordinary Ethernet LAN
- LoRa / LoRaWAN style radio
- Wi-Fi
- Bluetooth service/proximity links
- legacy Home wiring such as coax or telephone pair

Fields:

```yaml
network_type: string
latency_class: reflex | bounded | best_effort
bandwidth_class: low | medium | high
determinism: strict | bounded | weak | none
wiring_cost: low | medium | high
fault_isolation: low | medium | high
authority_allowed: read_only | bounded_command | none | emergency_only
power_over_link: boolean
multidrop_supported: boolean
timestamp_preservation_required: boolean
noise_test_required: boolean
```

## 3. 10BASE-T1S Research Track

10BASE-T1S should be tracked beside CAN, not treated as a CAN replacement.

Test questions:

- mixed CAN/Ethernet gateway behavior
- multidrop node failure
- noise injection
- timestamp preservation
- deterministic access
- power loss of one edge node
- packet flooding from a compromised sensor
- topology discovery integrity

## 4. Topology Integrity Contract

Networks should know what should exist, not merely what answered today.

Suggested fields:

```yaml
network_segment_id: string
expected_neighbors: [string]
observed_neighbors: [string]
missing_neighbors: [string]
unexpected_neighbors: [string]
link_health: map
topology_confidence: number
topology_changed: boolean
security_event_required: boolean
receipt_id: string
```

Rules:

- a missing node is a health event
- an unexpected node is a health/security event
- topology changes should be receipted before any new authority is considered

## 5. Trust Drift For Vehicle Sensors

Sensor confidence should evolve from behavior, not a fixed label.

Pattern:

```text
expected measurement -> actual measurement -> residual -> repeated bias -> trust adjustment
```

Suggested fields:

```yaml
sensor_id: string
expected_value: any
observed_value: any
residual: number | null
residual_window: [number]
bias_suspected: boolean
outlier_rejected: boolean
trust_adjustment: number
trust_reason: string
```

Use cases:

- GNSS
- IMU
- wheel-speed estimates
- CAN-derived speed/RPM
- camera odometry
- radar or ultrasonic perimeter sensors

## 6. Asymmetric Camera Link Note

Some future camera links may need massive upstream bandwidth and tiny downstream control bandwidth.

Track:

```yaml
link_id: string
upstream_bandwidth_required: string
downstream_bandwidth_required: string
link_asymmetry: symmetric | upstream_heavy | downstream_heavy
health_channel_required: boolean
control_channel_required: boolean
fallback_on_downstream_loss: string
```

## 7. Remote Sensor Pod Topology

A future pod should be a self-reporting organ, not a dumb firehose.

Pod elements:

- camera or sensor
- local MCU
- auxiliary sensors
- local timestamping
- link health counters
- error counters
- remote reset/power-cycle ability
- strain relief and mounting notes
- graceful degradation if an auxiliary sensor dies

Suggested path:

```text
remote sensor pod -> deterministic bridge/gateway -> Event Protocol -> fused observation
```

## 8. Vehicle Data Replay Requirement

Every vehicle adapter should declare replay support.

Fields:

```yaml
adapter_id: string
raw_capture_supported: boolean
normalized_capture_supported: boolean
replay_into_event_protocol: boolean
timestamp_preserving_playback: boolean
speed_adjusted_playback: boolean
fault_injection_during_replay: boolean
privacy_filtering_supported: boolean
receipt_linking_supported: boolean
```

## 9. Deployment Readiness For Vehicle Interfaces

A vehicle interface is not deployable merely because the PCB and code exist.

Track:

```yaml
interface_id: string
designed: boolean
parts_available: boolean
physically_provisioned: boolean
power_available: boolean
cooling_available: boolean
wiring_path_available: boolean
mount_available: boolean
network_path_available: boolean
bench_tested: boolean
vehicle_tested: boolean
deployable: boolean
```

## Non-goals

- No actuator enablement.
- No live vehicle writes by default.
- No automatic trust from network discovery.
- No replacement of existing read-only synthetic CAN posture without explicit review.

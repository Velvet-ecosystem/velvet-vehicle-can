# Velvet Vehicle CAN Module

**Read-only CAN subsystem for vehicle learning, fingerprinting, and safety qualification.**

## Overview

This module provides offline-first, vehicle-agnostic CAN bus learning capabilities for Velvet AI. It operates in read-only mode by default and learns vehicle control dialects through passive observation and correlation analysis.

## CAN Body Registry Contract

Velvet Vehicle CAN supports vehicle body discovery, signal classification, fingerprinting, and read-only telemetry, but detected CAN activity is not authority.

CAN-discovered signals begin as candidates. Write-capable behavior requires explicit registration, authorization, safety gating, and receipts.

See:

- [CAN Body Registry Contract](docs/can_body_registry_contract.md)

## What Velvet Vehicle CAN is

This repository contains the CAN bus interface layer used by Velvet AI to communicate with vehicle ECUs, perform diagnostics, and observe vehicle telemetry.

## Features

- **CAN Fingerprinting**: Identify vehicles by CAN traffic patterns + VIN hash
- **Dialect Learning**: Discover signal mappings through driver action correlation
- **Profile Storage**: Offline-first vehicle profiles (JSON)
- **Safety Qualification**: Stage-based capability gating with authority envelopes
- **Observation Events**: Stable read-only envelopes for runtime, receipts, UI, and organ consumers
- **Read-Only by Design**: No CAN injection or actuation logic

## Components

- `can_backend.py` - CAN reader adapters (SocketCAN, python-can, fake/test)
- `can_fingerprint.py` - Vehicle identification via traffic analysis
- `can_dialect_learner.py` - Machine learning for signal mapping
- `vehicle_profile.py` - Persistent vehicle profile storage
- `qualification_gate.py` - Safety-gated capability staging
- `can_sniffer_service.py` - Main orchestrator service
- `can_events.py` - Observation-only event envelopes
- `sniffer_runner.py` - Example standalone runner

## Installation

### Basic (software-only, testing)

```bash
pip install velvet-vehicle-can
```

### With hardware CAN support

```bash
pip install velvet-vehicle-can[hardware]
```

Hardware observation requires SocketCAN configured in kernel listen-only mode.

Do not guess the vehicle bitrate. Measure or confirm the bitrate for the specific bus before connecting the interface.

```bash
CAN_INTERFACE=can0
CAN_BITRATE=<verified_vehicle_bitrate>

sudo ip link set "$CAN_INTERFACE" down 2>/dev/null || true
sudo ip link set "$CAN_INTERFACE" type can \
  bitrate "$CAN_BITRATE" \
  listen-only on \
  restart-ms 0
sudo ip link set "$CAN_INTERFACE" up
```

Verify the effective kernel configuration before starting any reader:

```bash
ip -details -statistics link show "$CAN_INTERFACE"
```

The output must explicitly report:

```text
state UP
listen-only on
bitrate <verified_vehicle_bitrate>
```

A missing `listen-only on` line is a failed deployment. Leave the interface down and do not start the observer.

## Usage

### Standalone (no hardware)

```python
from velvet_vehicle_can import FakeCanReader, CanSnifferService

reader = FakeCanReader()
reader.push(can_id=0x123, data=b'\x00\x01\x02\x03\x04\x05\x06\x07')

service = CanSnifferService(read_frame=reader.read_frame)
service.tick()  # Process one frame
```

### Create observation events

```python
from velvet_vehicle_can import (
    build_can_observation_events,
    decode_signal_map,
)

decoded = decode_signal_map(observed_frames, vehicle_profile.signal_map)
events = build_can_observation_events(
    decoded,
    bus_name="obd_can",
    profile_digest=vehicle_profile.fingerprint_digest,
)

for event in events:
    runtime.publish(event.to_dict())
```

These events report observations only. They carry `authority: none` and cannot be used as direct vehicle-control commands.

### With hardware

Use the receive-only hardware interfaces after the kernel listen-only check has passed:

```python
from velvet_vehicle_can import (
    ListenOnlyCanConfig,
    ListenOnlyPythonCanReader,
    ReceiveOnlyCanObserver,
)

reader = ListenOnlyPythonCanReader(ListenOnlyCanConfig(channel="can0"))
observer = ReceiveOnlyCanObserver(reader.read_frame)

try:
    while True:
        frame = observer.observe()
        if frame is not None:
            print(frame.to_dict())
finally:
    reader.shutdown()
```

The library does not configure bitrate, link state, or listen-only mode. Those remain deployment responsibilities enforced before the reader starts.

## Safety

**This module does NOT perform CAN injection.**

It only:

- Reads CAN frames
- Learns signal mappings
- Produces observation-only events
- Provides qualification decisions

Kernel listen-only mode is required for live vehicle observation. Application-level receive-only classes are an additional boundary, not a replacement for the kernel setting.

Actual vehicle control must be implemented separately and must:

- Respect `QualificationResult` envelopes
- Implement kill switches
- Handle driver overrides immediately
- Validate checksums/counters before injection
- Use separate executors, policies, gates, and receipts
- Require explicit local deployment review

See `docs/can_learning_pipeline.md` for safety methodology.

## Documentation

- [CAN Learning Pipeline](docs/can_learning_pipeline.md) - Stage-based onboarding
- [Vehicle Dialects](docs/vehicle_dialects.md) - Philosophy and design
- [CAN Observation Event Contract](docs/can_observation_event_contract.md) - Runtime-facing read-only envelope

The full Founder-node SocketCAN deployment procedure lives in the `velvet-runtime` repository under `docs/founder_can_listen_only_deployment.md`.

## License

GPLv3 - See LICENSE file

## Dependencies

- **Required**: Python 3.8+, stdlib only
- **Optional**: `python-can>=4.0.0` (for hardware CAN access)

## Module Type

Hardware module - follows Velvet's modular architecture for pluggable vehicle subsystems.

# Velvet Vehicle CAN Module

**Read-only CAN subsystem for vehicle learning, fingerprinting, and safety qualification.**

## Overview

This module provides offline-first, vehicle-agnostic CAN bus learning capabilities for Velvet AI. It operates in read-only mode by default and learns vehicle control dialects through passive observation and correlation analysis.

## Features

- **CAN Fingerprinting**: Identify vehicles by CAN traffic patterns + VIN hash
- **Dialect Learning**: Discover signal mappings through driver action correlation
- **Profile Storage**: Offline-first vehicle profiles (JSON)
- **Safety Qualification**: Stage-based capability gating with authority envelopes
- **Read-Only by Design**: No CAN injection or actuation logic

## Components

- `can_backend.py` - CAN reader adapters (SocketCAN, python-can, fake/test)
- `can_fingerprint.py` - Vehicle identification via traffic analysis
- `can_dialect_learner.py` - Machine learning for signal mapping
- `vehicle_profile.py` - Persistent vehicle profile storage
- `qualification_gate.py` - Safety-gated capability staging
- `can_sniffer_service.py` - Main orchestrator service
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

Requires SocketCAN configured on Linux:
```bash
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
```

## Usage

### Standalone (no hardware)
```python
from velvet_vehicle_can import FakeCanReader, CanSnifferService

reader = FakeCanReader()
reader.push(can_id=0x123, data=b'\x00\x01\x02\x03\x04\x05\x06\x07')

service = CanSnifferService(read_frame=reader.read_frame)
service.tick()  # Process one frame
```

### With hardware
```python
from velvet_vehicle_can import PythonCanReader, SocketCanConfig, CanSnifferService

config = SocketCanConfig(channel="can0", bustype="socketcan")
reader = PythonCanReader(config)

service = CanSnifferService(read_frame=reader.read_frame)

while True:
    service.tick()
```

## Safety

**This module does NOT perform CAN injection.**

It only:
- Reads CAN frames
- Learns signal mappings
- Provides qualification decisions

Actual vehicle control must be implemented separately and must:
- Respect `QualificationResult` envelopes
- Implement kill switches
- Handle driver overrides immediately
- Validate checksums/counters before injection

See `docs/can_learning_pipeline.md` for safety methodology.

## Documentation

- [CAN Learning Pipeline](docs/can_learning_pipeline.md) - Stage-based onboarding
- [Vehicle Dialects](docs/vehicle_dialects.md) - Philosophy and design

## License

GPLv3 - See LICENSE file

## Dependencies

- **Required**: Python 3.8+, stdlib only
- **Optional**: `python-can>=4.0.0` (for hardware CAN access)

## Module Type

Hardware module - follows Velvet's modular architecture for pluggable vehicle subsystems.

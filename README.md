# Velvet Vehicle CAN

**Read-only vehicle-bus observation, decoding, fingerprinting, replay, and qualification support for the Velvet ecosystem.**

`velvet-vehicle-can` is the vehicle-facing evidence layer. It receives CAN frames, normalizes them, learns signal candidates, builds vehicle profiles, and publishes observation-only events for Runtime, receipts, interfaces, and Velvet's specialist organs.

It is not the authority layer, not a driving controller, and not a CAN-injection service.

> Vehicle CAN observes. Runtime binds. Court authorizes. Executors act. Receipts remember.

## Current Status

The repository currently provides a bounded read-only foundation for software tests, public Ghost demonstrations, bench replay, and listen-only vehicle observation.

Current CAN transmit authority: **none**.

Current physical actuation authority: **none**.

Implemented capabilities include:

- passive CAN frame observation
- fake/test readers for deterministic software tests
- SocketCAN and optional `python-can` receive adapters
- kernel listen-only deployment contract
- receive-only observer wrappers
- CAN traffic fingerprinting
- vehicle profile persistence
- candidate signal classification and decoding
- qualification envelopes for future capability review
- observation-only event envelopes
- synthetic Ghost CAN demo and fixture replay
- Runtime-facing read-only integration

The repository does **not** currently provide:

- CAN transmission
- message injection
- ECU control
- diagnostics write services
- relay or actuator control
- steering, throttle, braking, shifting, lock, lighting, climate, or drive authority
- any path that turns a discovered signal directly into permission

## System Boundary

```text
vehicle bus or synthetic fixture
  -> receive-only CAN adapter
  -> normalized frame
  -> fingerprint / profile / decoder
  -> observation-only event
  -> velvet-runtime
  -> Court / safety / execution contracts / receipts
  -> approved future executor, if one is ever explicitly enabled
```

A detected CAN identifier is evidence, not authority.

A decoded signal is evidence, not authority.

A vehicle profile is evidence, not authority.

A replay fixture is evidence, not authority.

Future write-capable behavior must live behind Runtime, Court, explicit policy, named safety gates, bounded execution contracts, replay protection, resource coordination, durable receipts, and local deployment review.

## Read-Only Law

```text
no verified listen-only kernel state = do not observe live hardware
no explicit vehicle bitrate = do not configure the interface
no registered profile = treat signals as candidates
no Court authorization = no future write-capable execution
no dedicated executor = no transmission
```

Application-level receive-only classes are an additional boundary. They do not replace kernel listen-only mode.

## Core Observation Flow

```text
CAN frame
  -> backend reader
  -> receive-only observer
  -> normalized frame record
  -> fingerprint update
  -> signal-map decode
  -> vehicle profile context
  -> observation event
  -> Runtime / receipts / UI / organ consumers
```

Observation events must remain explicit about their posture:

```text
authority: none
read_only: true
actuation_granted: false
actuation_performed: false
```

## CAN Body Registry Contract

Velvet Vehicle CAN supports vehicle-body discovery, signal classification, fingerprinting, and read-only telemetry, but discovered traffic never becomes authority by itself.

Signals begin as candidates. A future write path would require explicit registration, qualification, authorization, safety gating, execution contracts, resource ownership, and receipts.

See [CAN Body Registry Contract](docs/can_body_registry_contract.md).

## Main Components

- `can_backend.py` - SocketCAN, optional `python-can`, fake, and test reader adapters
- `receive_only.py` - receive-only configuration and observer boundaries
- `can_fingerprint.py` - traffic-pattern and profile fingerprint support
- `can_dialect_learner.py` - candidate signal learning and correlation support
- `vehicle_profile.py` - offline-first vehicle profile persistence
- `qualification_gate.py` - staged qualification envelopes for reviewed capabilities
- `can_sniffer_service.py` - observation orchestrator
- `can_events.py` - observation-only event envelopes
- `ghost_can_demo.py` - synthetic public demo and fixture replay path
- `sniffer_runner.py` - standalone observation example

## Installation

### Software-only testing

```bash
pip install velvet-vehicle-can
```

### Optional hardware support

```bash
pip install velvet-vehicle-can[hardware]
```

The base package requires Python 3.8 or newer and uses the standard library. Optional hardware support installs `python-can>=4.0.0`.

## Listen-Only Hardware Deployment

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

The library does not configure bitrate, link state, or listen-only mode. Those remain deployment responsibilities.

The full Founder-node deployment procedure lives in `velvet-runtime` under `docs/founder_can_listen_only_deployment.md`.

## Software-Only Example

```python
from velvet_vehicle_can import FakeCanReader, CanSnifferService

reader = FakeCanReader()
reader.push(can_id=0x123, data=b"\x00\x01\x02\x03\x04\x05\x06\x07")

service = CanSnifferService(read_frame=reader.read_frame)
service.tick()
```

## Observation Events

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

These events report observations only. They carry no direct vehicle-control authority.

See [CAN Observation Event Contract](docs/can_observation_event_contract.md).

## Live Receive-Only Example

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

This code assumes the deployment-side kernel check has already passed.

## Ghost CAN Demo

The public Ghost CAN loop proves that the repository can process vehicle-shaped telemetry without opening a hardware bus, sending a frame, or touching an actuator.

```text
synthetic CAN frame
  -> FakeCanReader
  -> ReceiveOnlyCanObserver
  -> learned-profile style decoder
  -> vehicle.can.ghost_observation
  -> Runtime / receipt / interface consumers
```

Run it with:

```bash
python -m velvet_vehicle_can.ghost_can_demo --pretty
python -m velvet_vehicle_can.ghost_can_demo \
  --fixture examples/fixtures/tiburon_ghost_frames.jsonl \
  --pretty
velvet-ghost-can --pretty
```

The demo always reports:

```text
read_only: true
hardware_bus_opened: false
actuation_granted: false
actuation_performed: false
```

See [Public Ghost CAN Demo](docs/ghost_can_demo.md).

## Fingerprints, Profiles, and Dialects

Fingerprinting and dialect learning help Velvet distinguish buses, vehicles, ECUs, and candidate signals over time.

The intended progression is:

```text
unknown traffic
  -> observed identifier and timing patterns
  -> fingerprint candidate
  -> vehicle-profile binding
  -> signal candidate
  -> correlated evidence
  -> reviewed decoder mapping
  -> qualified read-only observation
```

A learned correlation must not be presented as a guaranteed physical meaning until reviewed and validated against the vehicle profile.

See:

- [CAN Learning Pipeline](docs/can_learning_pipeline.md)
- [Vehicle Dialects](docs/vehicle_dialects.md)

## Qualification Boundary

Qualification results describe readiness evidence and safety posture. They do not authorize execution.

A future controlled transmit path would still require:

- a registered vehicle and bus profile
- known arbitration identifiers
- validated payload layout
- checksum and rolling-counter handling where applicable
- bounded targets and parameters
- dedicated Runtime executor
- Court policy and authority resolution
- named safety gate
- driver override and kill-switch behavior
- exclusive CAN-bus resource ownership
- durable start, completion, failure, and release receipts
- explicit local deployment review

No such transmit path is enabled here today.

## Runtime Integration

`velvet-runtime` is the authority and execution boundary.

This repository supplies receive-only adapters, decoded observations, profile context, and qualification evidence. Runtime supplies identity binding, Court authorization, execution contracts, resource coordination, safety gates, replay protection, approved executors, and receipts.

Current Runtime routes using this package remain read-only:

- `can-observe`
- `can-signals`

The CAN package must never accept a language-model response, UI gesture, remote request, or decoded signal as direct authority to transmit.

## Repository Structure

```text
velvet-vehicle-can/
├── pyproject.toml
├── velvet_vehicle_can/
│   ├── can_backend.py
│   ├── receive_only.py
│   ├── can_fingerprint.py
│   ├── can_dialect_learner.py
│   ├── vehicle_profile.py
│   ├── qualification_gate.py
│   ├── can_sniffer_service.py
│   ├── can_events.py
│   ├── ghost_can_demo.py
│   └── sniffer_runner.py
├── examples/
│   ├── ghost_can_demo.py
│   └── fixtures/
├── docs/
└── tests/
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests and Ghost fixtures should remain deterministic and hardware-free unless a test is explicitly marked for a controlled bench environment.

## Completed Foundation

- read-only backend abstraction
- fake and test frame sources
- SocketCAN and optional `python-can` observation adapters
- receive-only observer boundary
- fingerprint and vehicle-profile foundation
- candidate dialect-learning flow
- qualification envelopes
- observation-only event contract
- Runtime-facing observation path
- public Ghost CAN demo and fixture replay
- explicit body-registry and no-authority doctrine

## Next Milestones

1. Expand reviewed signal decoders and profile evidence.
2. Improve vehicle and bus adapter abstraction.
3. Add richer deterministic bench replay and comparison reports.
4. Strengthen fingerprint confidence and profile-change detection.
5. Refine Runtime compatibility and startup diagnostics.
6. Validate live listen-only observation on controlled hardware and preserve evidence bundles.
7. Design any future transmit path only as a separate doctrine-gated executor project after explicit local review.

## Security Posture

Velvet Vehicle CAN is offline-first, vehicle-agnostic, and read-only by default.

The decoder may describe what the bus appears to be doing. It may not decide what the vehicle should do.

Observation is not authorization. Qualification is not authorization. A profile is not authorization.

## Documentation

- [CAN Body Registry Contract](docs/can_body_registry_contract.md)
- [CAN Learning Pipeline](docs/can_learning_pipeline.md)
- [Vehicle Dialects](docs/vehicle_dialects.md)
- [CAN Observation Event Contract](docs/can_observation_event_contract.md)
- [Public Ghost CAN Demo](docs/ghost_can_demo.md)

## License

GPLv3. See [LICENSE](LICENSE).

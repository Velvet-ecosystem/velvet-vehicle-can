# Receive-Only CAN Body Adapter

The CAN body adapter turns passive CAN observations into Velvet's standard
SensorPacket and HealthEvent Event Protocol records.

It is the bridge between live vehicle data and the shared body contracts used by
Runtime, receipts, the Interface, and simulated hardware.

## Flow

```text
kernel listen-only CAN interface
  -> ListenOnlyPythonCanReader
  -> ReceiveOnlyCanObserver
  -> ReceiveOnlyCanBodyAdapter
  -> SensorPacket-shaped Event Protocol record
  -> optional HealthEvent-shaped transition
  -> Runtime / receipts / Interface
```

The same adapter also accepts `FakeCanReader` through `ReceiveOnlyCanObserver`,
so software tests and live hardware follow the same record path.

## Configuration

`CanBodyAdapterConfig` declares:

- module identity
- Founder or other node identity
- owning handmaiden
- bus name
- physical interface type
- stale interval
- calibration version
- source-clock type

The default owner is Ruby and the default node is `founder-up2`. Deployment code
should override those values when the adapter is bound elsewhere.

## Sensor records

Every observed frame produces a standard sensor record containing:

- module, node, and owner identity
- wall and monotonic timestamps
- sensor and interface type
- health and confidence
- raw CAN identifier, payload, DLC, and frame type
- stale interval and calibration version
- receipt identifier
- explicit read-only and no-actuation claims

Raw references use the bus and CAN identifier, allowing receipts and evidence
bundles to point back to the source observation.

## Health transitions

The adapter emits bounded health evidence:

- `ONLINE` after the first received frame
- `STALE` after the configured period without a frame
- `FAILED` when the receive path raises an exception
- `RECOVERED` when a frame arrives after degraded or failed state

A missing frame before the stale window expires is not treated as failure.
Repeated empty polls do not flood duplicate stale events.

## Authority boundary

`ReceiveOnlyCanBodyAdapter` deliberately exposes no method named:

- `send`
- `transmit`
- `write`
- `inject`
- `actuate`

The adapter cannot configure bitrate, bring up the interface, disable kernel
listen-only mode, transmit frames, or command a vehicle system.

```text
CAN hardware observes.
The body adapter normalizes evidence.
Runtime verifies and coordinates.
Court authorizes future bounded execution.
Receipts remember.
```

## Founder deployment

Before binding the adapter to `can0`, the UP2 deployment must prove:

- the correct vehicle bitrate was verified rather than guessed
- the interface is UP
- kernel `listen-only on` is present
- the receive backend is healthy
- the node manifest lists the CAN interface as observation-only

No verified listen-only kernel state means no live hardware observation.

## Next adapters

The same body-record pattern should be applied next to:

1. GNSS UART/NMEA input
2. ignition and voltage input
3. microphone capture health and level evidence
4. LD2410 and seat-presence JSON
5. camera stream health and frame evidence

Those adapters belong beside their physical-domain implementation, while the
SensorPacket and HealthEvent contracts remain shared.

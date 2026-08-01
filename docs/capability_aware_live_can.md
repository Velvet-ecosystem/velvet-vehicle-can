# Capability-Aware Live CAN Deployment

Velvet supports modern CAN-rich vehicles, older vehicles with limited dedicated
signals, and mixed retrofit bodies.  A vehicle profile is not judged by how many
signals it exposes.  It records only what that body can honestly provide and how
each fact reaches Runtime.

```text
modern CAN evidence
legacy hard-wired evidence
specialized retrofit evidence
        -> canonical vehicle signals
        -> source, confidence, freshness, and agreement
        -> Runtime body state and receipts
```

Signal availability does not grant authority.  Source agreement does not grant
authority.  A decoded frame does not prove its semantic meaning.

## Evidence topology

`VehicleProfile.evidence_topology` records one or more source bindings for each
canonical signal.

Source kinds are:

- `can`: passive vehicle-bus observation
- `obd_diagnostic`: read-only diagnostic observation
- `hardwired`: dedicated isolated electrical or analog input
- `specialized`: retrofit sensor or specialist controller

Source states are:

- `declared`: designed or expected, but not physically observed
- `detected`: the source exists and has produced evidence
- `verified`: physical behaviour has been checked against a known reference

A profile may declare overlapping sources.  Velvet preserves them rather than
allowing a modern CAN value to erase an independent hard-wired measurement.

### Modern example

```json
{
  "generation": "modern",
  "bindings": [
    {
      "canonical_signal": "vehicle.ignition.state",
      "source_kind": "can",
      "source_ref": "can:body",
      "transport": "socketcan:can0",
      "state": "verified",
      "priority": 10,
      "confidence_cap": 0.95,
      "independent": true
    },
    {
      "canonical_signal": "vehicle.power.voltage",
      "source_kind": "can",
      "source_ref": "can:powertrain",
      "transport": "socketcan:can0",
      "state": "verified",
      "priority": 10,
      "confidence_cap": 0.95,
      "independent": true
    }
  ]
}
```

### Legacy example

```json
{
  "generation": "legacy",
  "bindings": [
    {
      "canonical_signal": "vehicle.ignition.state",
      "source_kind": "hardwired",
      "source_ref": "gpio:ignition-isolated",
      "transport": "isolated-digital-input",
      "state": "verified"
    },
    {
      "canonical_signal": "vehicle.power.voltage",
      "source_kind": "hardwired",
      "source_ref": "adc:vehicle-voltage",
      "transport": "isolated-analog-input",
      "state": "verified"
    }
  ]
}
```

Missing speed, door, HVAC, or steering signals remain unavailable.  They do not
make the ignition and voltage observations less valid.

### Mixed example

A mixed vehicle may expose voltage through CAN and through an isolated analog
measurement.  When both are physically verified and independent, Runtime can
compare them while retaining both source identities.

```text
vehicle.power.voltage
  <- can:body
  <- adc:vehicle-voltage
```

Disagreement is evidence for degradation or investigation.  Agreement is higher
confidence, not permission.

## Physical SocketCAN setup

The live path is deliberately split into setup and observation:

```text
exact vehicle-specific bitrate
  -> kernel SocketCAN listen-only setup
  -> fail-closed preflight receipt
  -> Runtime receive-only body bridge
```

Never guess a bitrate.  Establish it from trusted vehicle documentation, a
validated interface configuration, or a separate controlled measurement.  The
presence of an OBD-style connector, tracker split, or CAN transceiver does not
prove the target bus, bitrate, protocol, or signal meanings.

Create a vehicle-specific environment file:

```bash
sudo install -d -m 0700 /etc/velvet/can
sudo sh -c 'umask 077; printf "%s\n" "VELVET_CAN_BITRATE=REPLACE_ME" > /etc/velvet/can/can0.env'
```

Install and enable the setup unit:

```bash
sudo install -m 0644 deploy/systemd/velvet-socketcan-listen-only@.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now velvet-socketcan-listen-only@can0.service
```

The service invokes:

```text
scripts/configure_socketcan_listen_only.sh can0 <exact-bitrate>
```

It brings the interface down, applies the exact bitrate with kernel
`listen-only on`, brings the interface up, and verifies the resulting link
details.  Any mismatch leaves the interface down.

The setup unit writes an owner-only preflight receipt to:

```text
/run/velvet/can/can0-preflight.json
```

The same check can be run manually:

```bash
velvet-can-preflight --channel can0
```

With a profile:

```bash
velvet-can-preflight \
  --channel can0 \
  --profile /var/lib/velvet/vehicle-profiles/<fingerprint>.json \
  --output /run/velvet/can/can0-preflight.json
```

A successful preflight proves only:

```text
interface_present: true
listen_only_verified: true
bitrate_verified: true
frames_received: false
signal_meaning_proven: false
transmission_attempted: false
authority_granted: false
actuation_performed: false
```

## Runtime observation

After the setup unit is green, Velvet Runtime's existing
`scripts/can_body_state_bridge.py` may open the interface through the
receive-only `ListenOnlyPythonCanReader`.  The backend has no public send,
transmit, write, or inject method, and the Runtime bridge independently verifies
kernel listen-only posture before reading frames.

Raw frames first prove bus activity.  Fingerprints then bind candidate profiles.
Decoded candidates become `ProfileObservation` values carrying:

- canonical signal name
- profile field
- CAN identifier
- source kind and source reference
- source state
- bounded confidence
- whether the source was explicitly declared
- whether an independent verified cross-check exists

A CAN-derived ignition or voltage observation is stored alongside any physical
input.  It does not overwrite the hard-wired source or inherit its verification.

## Vehicle classes

### Newer vehicles

Use CAN and diagnostic observations wherever the specific vehicle profile has
validated mappings.  Broad availability is expected, but nothing is accepted
merely because another model or model year broadcasts a similar identifier.

### Older vehicles

Use the limited CAN or diagnostic data actually present.  Add isolated
hard-wired inputs and specialized retrofit sensors only where useful.  A sparse
profile is normal.

### Retrofit and mixed vehicles

Preserve every independent source.  Prefer explicit source priority for display
or primary estimation while keeping the other sources available for comparison,
failure detection, and receipts.

## Safety boundary

This deployment adds no CAN transmission, diagnostic request, relay, wake
command, ECU write, actuator path, Runtime route, Court grant, or physical
control.  Physical Control remains disabled.

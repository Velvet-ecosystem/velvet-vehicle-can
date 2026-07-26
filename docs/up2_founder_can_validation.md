# UP² Founder CAN Validation

## Status

`velvet-vehicle-can` was installed from the local editable source tree and detected successfully during Velvet's first verified Founder Runtime boot on physical UP Squared hardware.

The verified visible posture was:

```text
Continuity        VERIFIED
Court             READY
Runtime           ACTIVE
Routes            READ-ONLY
Physical Control  DISABLED

Waiting for Mister
```

This validates package availability, import compatibility, Runtime discovery, and preservation of the read-only authority boundary on the Founder node.

It does **not** validate a live vehicle CAN connection.

## What Was Proven

The Founder session established that:

- the `velvet-vehicle-can` distribution was installed in the same Python environment used by Runtime
- the `velvet_vehicle_can` import surface was available to the physical UP² host
- Runtime could discover the package without granting CAN transmit authority
- the Founder snapshot preserved read-only routes and disabled physical control
- the CAN repository could participate in the installed ecosystem without becoming a parallel authority lane
- missing or stale package state was reported honestly rather than silently ignored

The package inventory included an editable source-tree installation similar to:

```text
velvet-vehicle-can  0.1.0  /home/coyote/velvet/velvet-vehicle-can
```

Editable installation is useful for development because the Founder node follows the checked-out repository. It does not replace version pinning or release qualification for production deployment.

## What Was Not Proven

The session did not establish any of the following:

- a physical CAN interface was connected
- `can0` or another SocketCAN interface existed
- a vehicle bitrate was measured or confirmed
- kernel listen-only mode was enabled and verified
- live CAN frames were received
- the Tiburon bus or any ECU was fingerprinted
- a vehicle profile was validated against physical signals
- decoded values matched real vehicle behaviour
- CAN traffic was persisted as a complete receipt bundle
- CAN transmission was attempted or available
- any actuator or vehicle function was controlled

The correct conclusion is therefore:

> CAN package integration on the Founder node was validated. Live listen-only vehicle-bus observation remains unvalidated.

## Authority Boundary

The physical Founder boot did not alter the repository's authority posture:

```text
CAN transmit authority       none
physical actuation authority none
Runtime routes               read-only
physical control             disabled
```

A package import, decoded signal, profile match, Ghost fixture, UI request, language-model output, or event does not authorize transmission.

Any future write-capable work must remain a separate reviewed executor path behind Runtime, Court, explicit policy, named safety gates, execution contracts, resource ownership, replay protection, durable receipts, and local deployment approval.

## Safe Live-Observation Milestone

The next physical CAN milestone should remain observation-only and must proceed in this order:

1. identify the exact interface hardware and electrical connection
2. confirm the target vehicle bus and bitrate without guessing
3. configure SocketCAN with kernel `listen-only on`
4. verify the effective link details before starting a reader
5. capture a short bounded frame sample
6. record interface, bitrate, timestamps, frame counts, errors, and listen-only evidence
7. produce a deterministic fingerprint and candidate profile
8. compare decoded candidates against known physical observations
9. publish observation-only events through Runtime
10. persist a receipt bundle that explicitly states no transmission and no actuation occurred
11. leave the interface down on any configuration uncertainty or mismatch

A successful first live run should end with evidence equivalent to:

```text
interface_present: true
listen_only_verified: true
bitrate_verified: true
frames_received: true
can_transmission_attempted: false
actuation_performed: false
authority_granted: false
```

## Ghost Versus Physical Evidence

Ghost CAN remains valuable for deterministic software and cross-repository testing, but it must stay visibly synthetic.

```text
Ghost fixture processed      != physical bus observed
physical bus observed        != signal meaning proven
signal meaning reviewed      != authority granted
authority granted            != execution completed
```

Each transition requires its own evidence and contract.

## Interpreter and Installation Rule

Use the same explicit Python interpreter for installation, diagnostics, snapshot generation, and launch. A package installed under one interpreter may appear absent to Runtime under another.

Example development installation:

```bash
PYTHON=/home/coyote/.pyenv/versions/3.10.20/bin/python3
$PYTHON -m pip install -e ~/velvet/velvet-vehicle-can
$PYTHON -m pip show velvet-vehicle-can
$PYTHON -c 'import velvet_vehicle_can; print(velvet_vehicle_can.__file__)'
```

Distribution and import names are different:

```text
distribution: velvet-vehicle-can
import:       velvet_vehicle_can
```

Runtime diagnostics should account for that distinction.

## Snapshot Rule

The Founder window displays the supplied snapshot. It does not independently prove that the current host state still matches an old file.

After package, policy, identity, route, or state changes:

1. source the intended Runtime environment
2. run diagnostics using the intended interpreter
3. generate a fresh boot snapshot
4. launch Interface from that fresh snapshot

A stale green snapshot is presentation of earlier evidence, not proof of current CAN readiness.

## Next Validation Targets

- cold-boot package rediscovery
- deterministic Ghost replay through Event Protocol and Receipts
- controlled bench replay with preserved fixtures
- physical SocketCAN listen-only verification
- bounded live Tiburon frame capture
- fingerprint and profile-change evidence
- decoded-signal correlation with known vehicle state
- complete observation event and receipt timeline
- recovery behaviour after interface loss or malformed frames
- later Luckfox read-only observer-node validation

## Final Statement

The first verified Founder boot proved that Velvet Vehicle CAN could join the physical UP² software body while remaining firmly observation-only.

The next proof is not transmission. It is a careful, receipted, kernel-verified listen-only encounter with a real vehicle bus.

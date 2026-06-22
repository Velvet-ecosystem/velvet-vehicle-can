# Receive-Only CAN Observer

Velvet Vehicle CAN observes frames. It does not transmit them.

The public observation path is:

```text
kernel listen-only CAN interface
  -> ListenOnlyPythonCanReader.read_frame()
  -> ReceiveOnlyCanObserver.observe()
  -> bounded ObservedCanFrame
  -> Runtime read-only telemetry adapter
```

Neither public adapter exposes a `send`, `transmit`, `write`, `inject`, or `actuate` method.

`ListenOnlyPythonCanReader` requests python-can PASSIVE state when supported and disables reception of locally generated frames. The underlying bus is private to the adapter.

Deployment must also configure the Linux CAN interface in kernel listen-only mode. The Python boundary provides API containment, not a malicious-code sandbox and not a replacement for host-level CAN configuration.

Observed classic CAN frames are normalized to:

```text
timestamp
can_id
can_id_hex
data_hex
dlc
extended
read_only: true
actuation_performed: false
```

Malformed identifiers and classic CAN payloads longer than eight bytes are rejected.

Any future CAN transmission implementation belongs behind Velvet Runtime Court authorization, an explicit write-capable manifest, a named safety gate, an approved executor, replay protection, physical presence requirements, and receipts. It must not be added to these observation classes.

# Physical CAN passive-mode enforcement

Every physical reader open now requires canonical `ip -json -details link` evidence
before backend construction and again immediately afterward. The JSON `ctrlmode`
array must contain `LISTEN-ONLY`; the configuration words `listen-only on` and the
text diagnostic `<LISTEN-ONLY>` are not parsed as JSON. An old/missing iproute2,
malformed/duplicate/ambiguous output, DOWN or non-CAN interface, unknown mode,
loopback/presume-ACK, missing bitrate or inactive controller refuses admission.

The configurator delegates verification to the same Python preflight with the
independently established expected bitrate. No fallback silently accepts weaker
text evidence. Target images must support iproute2 JSON; Ubuntu 20 commissioning
must confirm its exact output. Tests use representative synthetic iproute2 output,
not claimed captures from a commissioned controller.

`PythonCanReader` keeps receive/shutdown APIs but delegates to the guarded reader;
its raw public `.bus` is removed. Physical adapters accept SocketCAN only. Use
`FakeCanReader` for simulation. Runtime's wrapper delegates to this package rather
than maintaining a second parser. No send/write method or physical authority is
introduced. Backend recheck failure closes it before receiving any frame.

Readers must not have CAP_NET_ADMIN. A separately privileged setup supervisor owns
controller configuration; a later privileged mode change remains a deployment
fault that requires bench supervision. Source checks do not prove electrical
passivity, correct wiring/bitrate, kernel-driver support or vehicle signal meaning.
An isolated physical CAN bench is required before vehicle attachment.

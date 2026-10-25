#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail

usage() {
  echo "usage: $0 <interface> <bitrate>" >&2
  echo "The bitrate must be independently established; this script never guesses." >&2
}

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

interface=$1
bitrate=$2

if [[ ! $interface =~ ^[A-Za-z0-9_.:-]{1,32}$ ]]; then
  echo "invalid CAN interface name" >&2
  exit 2
fi
if [[ ! $bitrate =~ ^[0-9]+$ ]] || (( bitrate < 10000 || bitrate > 1000000 )); then
  echo "bitrate must be an integer between 10000 and 1000000" >&2
  exit 2
fi
if ! command -v ip >/dev/null 2>&1; then
  echo "iproute2 is required" >&2
  exit 2
fi

rollback() {
  ip link set dev "$interface" down >/dev/null 2>&1 || true
}
trap rollback ERR

ip link show dev "$interface" >/dev/null
ip link set dev "$interface" down
ip link set dev "$interface" type can bitrate "$bitrate" listen-only on
ip link set dev "$interface" up

# One canonical verifier owns parsing; no grep of configuration syntax.
"${VELVET_CAN_PYTHON:-python3}" -m velvet_vehicle_can.founder_can_preflight \
  --channel "$interface" --expected-bitrate "$bitrate"
trap - ERR
printf 'Velvet CAN posture: receive-only, bitrate=%s, interface=%s\n' "$bitrate" "$interface"

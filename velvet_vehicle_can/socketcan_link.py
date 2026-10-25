# SPDX-License-Identifier: GPL-3.0-only
"""Fail-closed inspection of a Linux SocketCAN listen-only link."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


_CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")
Runner = Callable[..., Any]


class SocketCanLinkError(ValueError):
    """Raised when the host cannot prove a safe receive-only CAN posture."""


@dataclass(frozen=True)
class SocketCanLinkEvidence:
    channel: str
    bitrate: int
    can_state: str
    captured_at: float
    details_sha256: str
    is_up: bool = True
    listen_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "velvet.vehicle.socketcan_link_evidence.v1",
            "channel": self.channel,
            "bitrate": self.bitrate,
            "can_state": self.can_state,
            "captured_at": self.captured_at,
            "details_sha256": self.details_sha256,
            "is_up": self.is_up,
            "listen_only": self.listen_only,
            "mode": "receive-only",
            "transmission_attempted": False,
            "transmission_available_to_service": False,
            "authority": "none",
            "grants_authority": False,
            "actuation_granted": False,
            "actuation_performed": False,
        }


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate kernel evidence field")
        value[key] = item
    return value


def inspect_socketcan_link(
    channel: str, *, runner: Optional[Runner] = None,
    now: Optional[float] = None, expected_bitrate: Optional[int] = None,
) -> SocketCanLinkEvidence:
    """Require unambiguous iproute2 JSON evidence; never configure an interface.

    JSON support is required. Malformed/unsupported output never falls back to
    interpreting configuration syntax as proof. Source configuration is owned by
    a separately privileged supervisor; reader processes must lack NET_ADMIN.
    """
    if not isinstance(channel, str) or not _CHANNEL_PATTERN.fullmatch(channel):
        raise SocketCanLinkError("invalid CAN channel")
    if expected_bitrate is not None and (type(expected_bitrate) is not int or not 10000 <= expected_bitrate <= 1000000):
        raise SocketCanLinkError("invalid expected bitrate")
    try:
        response = (runner or subprocess.run)(
            ["ip", "-json", "-details", "link", "show", "dev", channel],
            text=True, capture_output=True, timeout=3, check=False,
        )
        output = response.stdout or ""
        if response.returncode != 0 or response.stderr or not 1 <= len(output) <= 65536:
            raise ValueError("missing or failed structured interface evidence")
        entries = json.loads(output, object_pairs_hook=_unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid number")))
        if not isinstance(entries, list) or len(entries) != 1:
            raise ValueError("expected exactly one interface")
        entry = entries[0]
        if not isinstance(entry, dict) or entry.get("ifname") != channel:
            raise ValueError("interface identity mismatch")
        if type(entry.get("ifindex")) is not int or entry["ifindex"] <= 0:
            raise ValueError("missing interface index")
        flags = entry.get("flags")
        if not isinstance(flags, list) or any(not isinstance(x, str) for x in flags) or "UP" not in flags:
            raise ValueError("SocketCAN link is not UP")
        if entry.get("operstate") not in {"UP", "UNKNOWN"}:
            raise ValueError("SocketCAN operational state is unsafe")
        info = entry["linkinfo"]
        if info["info_kind"] != "can":
            raise ValueError("physical CAN interface required")
        data = info["info_data"]
        modes = data.get("ctrlmode")
        benign = {"LISTEN-ONLY", "TRIPLE-SAMPLING", "BERR-REPORTING", "FD", "FD-NON-ISO", "CC-LEN8-DLC", "ONE-SHOT"}
        if not isinstance(modes, list) or any(not isinstance(x, str) for x in modes) or "LISTEN-ONLY" not in modes or set(modes) - benign:
            raise ValueError("kernel listen-only mode is not unambiguously verified")
        state = data.get("state")
        if state not in {"ERROR-ACTIVE", "ERROR-WARNING", "ERROR-PASSIVE"}:
            raise ValueError("CAN controller state is unavailable or unsafe")
        bitrate = data["bittiming"]["bitrate"]
        if type(bitrate) is not int or not 10000 <= bitrate <= 1000000:
            raise ValueError("unsupported or missing bitrate")
        if expected_bitrate is not None and bitrate != expected_bitrate:
            raise ValueError("kernel bitrate differs from independently established bitrate")
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise SocketCanLinkError("cannot verify passive SocketCAN link: %s" % exc) from exc
    return SocketCanLinkEvidence(
        channel=channel, bitrate=bitrate, can_state=state,
        captured_at=time.time() if now is None else _non_negative(now, "now"),
        details_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest(),
    )


def build_live_can_preflight_receipt(
    link: SocketCanLinkEvidence,
    *,
    profile: Optional[Any] = None,
) -> Mapping[str, Any]:
    """Build one observation-only deployment receipt.

    ``profile`` is intentionally duck-typed so this module remains independent
    of the profile store.  When supplied, it must expose ``fingerprint_digest``
    and ``evidence_topology``.
    """

    if not isinstance(link, SocketCanLinkEvidence):
        raise TypeError("link must be SocketCanLinkEvidence")
    profile_payload = None
    if profile is not None:
        fingerprint = getattr(profile, "fingerprint_digest", None)
        topology = getattr(profile, "evidence_topology", None)
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError("profile fingerprint_digest must be non-empty")
        if topology is None or not callable(getattr(topology, "to_dict", None)):
            raise ValueError("profile evidence_topology is unavailable")
        profile_payload = {
            "fingerprint_digest": fingerprint,
            "evidence_topology": topology.to_dict(),
        }

    return {
        "schema": "velvet.vehicle.live_can_preflight.v1",
        "captured_at": link.captured_at,
        "link": link.to_dict(),
        "profile": profile_payload,
        "interface_present": True,
        "listen_only_verified": True,
        "bitrate_verified": True,
        "frames_received": False,
        "signal_meaning_proven": False,
        "transmission_attempted": False,
        "authority_granted": False,
        "actuation_performed": False,
        "next_step": "bounded receive-only frame observation",
    }


def _non_negative(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be numeric" % label)
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("%s cannot be negative" % label)
    return number

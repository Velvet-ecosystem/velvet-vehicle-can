# SPDX-License-Identifier: GPL-3.0-only
"""Fail-closed inspection of a Linux SocketCAN listen-only link."""

from __future__ import annotations

import hashlib
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


_CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")
_BITRATE_PATTERN = re.compile(r"\bbitrate\s+(\d+)\b", re.IGNORECASE)
_CAN_STATE_PATTERN = re.compile(r"\bcan\s+state\s+([A-Za-z-]+)", re.IGNORECASE)
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


def inspect_socketcan_link(
    channel: str,
    *,
    runner: Runner = subprocess.run,
    now: Optional[float] = None,
) -> SocketCanLinkEvidence:
    """Return bounded evidence only when Linux proves UP + listen-only + bitrate."""

    if not isinstance(channel, str) or not _CHANNEL_PATTERN.fullmatch(channel):
        raise SocketCanLinkError("invalid CAN channel")
    try:
        result = runner(
            ["ip", "-details", "link", "show", "dev", channel],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise SocketCanLinkError("cannot inspect SocketCAN link: %s" % exc)

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    lowered = output.lower()
    if result.returncode != 0:
        raise SocketCanLinkError("SocketCAN inspection failed: %s" % output)
    if not output:
        raise SocketCanLinkError("SocketCAN inspection returned no evidence")
    if (
        "state up" not in lowered
        and ",up," not in lowered
        and "<up," not in lowered
    ):
        raise SocketCanLinkError("SocketCAN link is not UP")
    if "listen-only on" not in lowered:
        raise SocketCanLinkError("SocketCAN link is not in kernel listen-only mode")

    bitrate_match = _BITRATE_PATTERN.search(output)
    if bitrate_match is None:
        raise SocketCanLinkError("SocketCAN bitrate is absent from link evidence")
    bitrate = int(bitrate_match.group(1))
    if not 10000 <= bitrate <= 1000000:
        raise SocketCanLinkError("SocketCAN bitrate is outside supported bounds")

    state_match = _CAN_STATE_PATTERN.search(output)
    can_state = state_match.group(1).upper() if state_match else "UNKNOWN"
    captured_at = time.time() if now is None else _non_negative(now, "now")
    return SocketCanLinkEvidence(
        channel=channel,
        bitrate=bitrate,
        can_state=can_state,
        captured_at=captured_at,
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
    if number < 0:
        raise ValueError("%s cannot be negative" % label)
    return number

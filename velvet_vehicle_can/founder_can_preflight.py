# SPDX-License-Identifier: GPL-3.0-only
"""Founder CLI for read-only physical CAN deployment evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from .socketcan_link import build_live_can_preflight_receipt, inspect_socketcan_link
from .vehicle_profile import VehicleProfileStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a live SocketCAN interface is UP and kernel listen-only"
    )
    parser.add_argument(
        "--channel",
        default=os.environ.get("VELVET_CAN_INTERFACE", "can0"),
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="optional vehicle-profile JSON containing evidence topology",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional owner-only JSON receipt path",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = None
        if args.profile is not None:
            profile = VehicleProfileStore(str(args.profile.parent)).load_path(args.profile)
        link = inspect_socketcan_link(args.channel)
        receipt = build_live_can_preflight_receipt(link, profile=profile)
        rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            _write_owner_only(args.output, rendered)
        sys.stdout.write(rendered)
        return 0
    except Exception as exc:
        print("Founder CAN preflight blocked: %s" % exc, file=sys.stderr)
        return 2


def _write_owner_only(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".%s." % path.name,
        dir=str(path.parent),
        text=True,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
        os.chmod(str(path), 0o600)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())

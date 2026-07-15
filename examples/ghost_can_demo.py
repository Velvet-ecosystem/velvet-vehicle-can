#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convenience wrapper for the public-safe ghost CAN demo."""

from velvet_vehicle_can.ghost_can_demo import main

if __name__ == "__main__":
    raise SystemExit(main())

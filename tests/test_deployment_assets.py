# SPDX-License-Identifier: GPL-3.0-only

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentAssetTests(unittest.TestCase):
    def test_listen_only_configurator_has_valid_bash_syntax(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is unavailable")
        script = ROOT / "scripts" / "configure_socketcan_listen_only.sh"

        result = subprocess.run(
            [bash, "-n", str(script)],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_systemd_template_requires_exact_bitrate_and_preflight(self):
        unit = (
            ROOT
            / "deploy"
            / "systemd"
            / "velvet-socketcan-listen-only@.service"
        ).read_text(encoding="utf-8")

        self.assertIn("EnvironmentFile=/etc/velvet/can/%i.env", unit)
        self.assertIn("${VELVET_CAN_BITRATE}", unit)
        self.assertIn("founder_can_preflight", unit)
        self.assertIn("CAP_NET_ADMIN", unit)
        self.assertNotIn("candump", unit)
        self.assertNotIn("cansend", unit)

    def test_example_environment_never_supplies_a_guessed_bitrate(self):
        example = (
            ROOT / "deploy" / "systemd" / "can0.env.example"
        ).read_text(encoding="utf-8")

        self.assertIn("REPLACE_WITH_VERIFIED_BITRATE", example)
        self.assertNotIn("500000", example)
        self.assertNotIn("250000", example)


if __name__ == "__main__":
    unittest.main()

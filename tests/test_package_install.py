# SPDX-License-Identifier: GPL-3.0-only

import unittest

import velvet_vehicle_can


class VehicleCanPackageTests(unittest.TestCase):
    def test_public_package_imports(self):
        self.assertTrue(hasattr(velvet_vehicle_can, "FakeCanReader"))
        self.assertTrue(hasattr(velvet_vehicle_can, "ReceiveOnlyCanObserver"))
        self.assertTrue(hasattr(velvet_vehicle_can, "QualificationGate"))


if __name__ == "__main__":
    unittest.main()

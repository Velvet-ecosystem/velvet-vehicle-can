# velvet_vehicle_can/__init__.py
"""
Vehicle CAN subsystem (CAN dialects, fingerprinting, profiles, learning, qualification, sniffing, and CAN backends).

This package is responsible for:
- Identifying a vehicle (VIN hash + CAN fingerprint)
- Storing per-vehicle learned profiles (SignalMap, confidence, stage)
- Learning CAN dialect candidates from passive observation (read-only)
- Determining what level of control is allowed via safety-gated qualification
- Providing a read-only CAN sniffer service that manages profiles + health + qualification
- Providing CAN backend adapters (read-only frame intake)
- Providing primitives used by higher-level driving and UI controllers

Safety note:
This package itself does NOT perform CAN injection.
It only learns, represents, and qualifies mappings and identities.
Actual control must pass through qualification gates.
"""

# --- Fingerprinting ---
from .can_fingerprint import (
    CanFingerprint,
    CanFingerprintBuilder,
    CanIdStats,
    hash_vin,
)

# --- Vehicle profiles & learned signal maps ---
from .vehicle_profile import (
    VehicleProfile,
    VehicleProfileStore,
    SignalMap,
    SignalDef,
    IntegrityRule,
)

# --- CAN dialect learning ---
from .can_dialect_learner import (
    CanDialectLearner,
    LabeledEvent,
    TelemetrySample,
    CanFrame,
)

# --- Qualification & safety gating ---
from .qualification_gate import (
    CapabilityStage,
    DriverState,
    HealthState,
    AuthorityEnvelope,
    QualificationResult,
    QualificationGate,
)

# --- CAN sniffer service (read-only) ---
from .can_sniffer_service import (
    CanSnifferService,
    SnifferConfig,
    VehicleRuntimeState,
)

# --- CAN backend adapters (read-only) ---
from .can_backend import (
    CanReader,
    SocketCanConfig,
    PythonCanReader,
    FakeCanReader,
)

__all__ = [
    # fingerprint
    "CanFingerprint",
    "CanFingerprintBuilder",
    "CanIdStats",
    "hash_vin",

    # profiles
    "VehicleProfile",
    "VehicleProfileStore",
    "SignalMap",
    "SignalDef",
    "IntegrityRule",

    # learning
    "CanDialectLearner",
    "LabeledEvent",
    "TelemetrySample",
    "CanFrame",

    # qualification
    "CapabilityStage",
    "DriverState",
    "HealthState",
    "AuthorityEnvelope",
    "QualificationResult",
    "QualificationGate",

    # sniffer
    "CanSnifferService",
    "SnifferConfig",
    "VehicleRuntimeState",

    # backend
    "CanReader",
    "SocketCanConfig",
    "PythonCanReader",
    "FakeCanReader",
]

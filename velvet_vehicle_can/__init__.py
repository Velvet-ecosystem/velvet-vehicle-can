# velvet_vehicle_can/__init__.py
"""Vehicle CAN learning, fingerprinting, and receive-only observation."""

from .can_fingerprint import CanFingerprint, CanFingerprintBuilder, CanIdStats, hash_vin
from .vehicle_profile import VehicleProfile, VehicleProfileStore, SignalMap, SignalDef, IntegrityRule
from .can_dialect_learner import CanDialectLearner, LabeledEvent, TelemetrySample, CanFrame
from .qualification_gate import (
    CapabilityStage,
    DriverState,
    HealthState,
    AuthorityEnvelope,
    QualificationResult,
    QualificationGate,
)
from .can_sniffer_service import CanSnifferService, SnifferConfig, VehicleRuntimeState
from .can_backend import CanReader, SocketCanConfig, PythonCanReader, FakeCanReader
from .can_observer import ObservedCanFrame, ReceiveOnlyCanObserver, normalize_observed_frame
from .listen_only_backend import ListenOnlyCanConfig, ListenOnlyPythonCanReader
from .signal_decoder import (
    DecodedSignal,
    decode_signal,
    decode_signal_map,
    summarize_decoded_signals,
)
from .signal_registry import (
    CANONICAL_SIGNAL_CATALOG,
    SignalCatalogEntry,
    SignalLifecycle,
    can_transition_signal,
    canonical_name_for,
    get_signal_by_name,
    get_signal_by_profile_field,
    validate_catalog,
)
from .can_events import (
    CAN_OBSERVATION_EVENT,
    CAN_OBSERVATION_SCHEMA,
    CanObservationEvent,
    build_can_observation_events,
    summarize_can_observation_events,
)

__all__ = [
    "CanFingerprint",
    "CanFingerprintBuilder",
    "CanIdStats",
    "hash_vin",
    "VehicleProfile",
    "VehicleProfileStore",
    "SignalMap",
    "SignalDef",
    "IntegrityRule",
    "CanDialectLearner",
    "LabeledEvent",
    "TelemetrySample",
    "CanFrame",
    "CapabilityStage",
    "DriverState",
    "HealthState",
    "AuthorityEnvelope",
    "QualificationResult",
    "QualificationGate",
    "CanSnifferService",
    "SnifferConfig",
    "VehicleRuntimeState",
    "CanReader",
    "SocketCanConfig",
    "PythonCanReader",
    "FakeCanReader",
    "ObservedCanFrame",
    "ReceiveOnlyCanObserver",
    "normalize_observed_frame",
    "ListenOnlyCanConfig",
    "ListenOnlyPythonCanReader",
    "DecodedSignal",
    "decode_signal",
    "decode_signal_map",
    "summarize_decoded_signals",
    "CANONICAL_SIGNAL_CATALOG",
    "SignalCatalogEntry",
    "SignalLifecycle",
    "can_transition_signal",
    "canonical_name_for",
    "get_signal_by_name",
    "get_signal_by_profile_field",
    "validate_catalog",
    "CAN_OBSERVATION_EVENT",
    "CAN_OBSERVATION_SCHEMA",
    "CanObservationEvent",
    "build_can_observation_events",
    "summarize_can_observation_events",
]

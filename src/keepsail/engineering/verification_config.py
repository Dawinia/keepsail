"""Compatibility imports for the shared verification configuration parser."""

from keepsail.core.verification_config import (
    INTERPOLATION_ALLOWLIST,
    CheckSpec,
    Command,
    Defaults,
    Execution,
    InterpolationError,
    Layers,
    VerificationCheckConflict,
    VerificationConfig,
    VerificationConfigError,
    interpolate,
    load_verification_config,
    merge_adapter_provided,
    merge_adapter_provided_list,
    parse_verification_config,
    required_check_contract,
)

__all__ = [
    "INTERPOLATION_ALLOWLIST",
    "CheckSpec",
    "Command",
    "Defaults",
    "Execution",
    "InterpolationError",
    "Layers",
    "VerificationCheckConflict",
    "VerificationConfig",
    "VerificationConfigError",
    "interpolate",
    "load_verification_config",
    "merge_adapter_provided",
    "merge_adapter_provided_list",
    "parse_verification_config",
    "required_check_contract",
]

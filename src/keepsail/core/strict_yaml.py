"""Strict YAML and literal-path parsing shared by committed policy readers."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import yaml

from keepsail.core.approval import ApprovalError


class _UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _UniqueLoader, node: yaml.MappingNode) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ApprovalError("duplicate or non-string key in policy configuration")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def parse_unique_yaml(text: str) -> object:
    """Parse YAML without silently accepting duplicate or non-string keys."""
    try:
        return yaml.load(text, Loader=_UniqueLoader)
    except yaml.YAMLError as exc:
        raise ApprovalError(f"policy configuration is invalid: {exc}") from exc


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ApprovalError(f"{label} must be non-empty text")
    return value


def literal_paths(value: object, *, label: str = "scope") -> list[str]:
    """Validate a non-empty list of unique, literal repository-relative paths."""
    if not isinstance(value, list) or not value:
        raise ApprovalError(f"{label} must be a non-empty list")
    result: list[str] = []
    for item in value:
        path = _text(item, f"{label} path")
        bare = path[:-1] if path.endswith("/") else path
        parsed = PurePosixPath(bare)
        if (not bare or parsed.is_absolute() or parsed.as_posix() != bare
                or any(part in {".", ".."} for part in bare.split("/"))
                or any(ch in path for ch in "\\*?[]\x00") or path in result):
            raise ApprovalError(f"{label} must contain unique literal repository paths")
        result.append(path)
    return result

"""Configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Severity

DEFAULT_THRESHOLDS: dict[str, int] = {
    "title_min": 30,
    "title_max": 60,
    "description_min": 70,
    "description_max": 160,
    "content_units_min": 300,
}


@dataclass(frozen=True)
class CheckerConfig:
    thresholds: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    disabled_rules: frozenset[str] = frozenset()
    severity_overrides: dict[str, Severity] = field(default_factory=dict)
    required_schema_types: tuple[str, ...] = ()

    @classmethod
    def from_path(cls, path: str | Path | None) -> CheckerConfig:
        if path is None:
            return cls()
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("configuration root must be a JSON object")
        thresholds = dict(DEFAULT_THRESHOLDS)
        supplied_thresholds = raw.get("thresholds", {})
        if not isinstance(supplied_thresholds, dict):
            raise TypeError("thresholds must be a JSON object")
        for key, value in supplied_thresholds.items():
            if key not in thresholds:
                raise ValueError(f"unknown threshold: {key}")
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"threshold {key} must be a non-negative integer")
            thresholds[key] = value

        disabled = raw.get("disabled_rules", [])
        required_types = raw.get("required_schema_types", [])
        overrides = raw.get("severity_overrides", {})
        if not isinstance(disabled, list) or not all(
            isinstance(item, str) for item in disabled
        ):
            raise ValueError("disabled_rules must be a list of strings")
        if not isinstance(required_types, list) or not all(
            isinstance(item, str) for item in required_types
        ):
            raise ValueError("required_schema_types must be a list of strings")
        if not isinstance(overrides, dict):
            raise TypeError("severity_overrides must be a JSON object")
        severity_overrides: dict[str, Severity] = {}
        for rule_id, value in overrides.items():
            try:
                severity_overrides[rule_id] = Severity(value)
            except ValueError as exc:
                raise ValueError(
                    f"severity override for {rule_id} must be error, warning, or info"
                ) from exc
        return cls(
            thresholds=thresholds,
            disabled_rules=frozenset(disabled),
            severity_overrides=severity_overrides,
            required_schema_types=tuple(required_types),
        )

    def severity(self, rule_id: str, default: Severity) -> Severity:
        return self.severity_overrides.get(rule_id, default)

    def is_enabled(self, rule_id: str) -> bool:
        return rule_id not in self.disabled_rules

    def to_dict(self) -> dict[str, Any]:
        return {
            "thresholds": self.thresholds,
            "disabled_rules": sorted(self.disabled_rules),
            "severity_overrides": {
                key: value.value for key, value in self.severity_overrides.items()
            },
            "required_schema_types": list(self.required_schema_types),
        }

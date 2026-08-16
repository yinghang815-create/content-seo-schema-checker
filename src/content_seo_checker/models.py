"""Shared data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    source: str
    suggestion: str | None = None
    evidence: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["severity"] = self.severity.value
        return result


@dataclass
class Document:
    source: str
    input_format: str
    title: str | None = None
    description: str | None = None
    canonical: str | None = None
    robots: list[str] = field(default_factory=list)
    lang: str | None = None
    headings: list[tuple[int, str, int | None]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    schemas: list[Any] = field(default_factory=list)
    schema_errors: list[str] = field(default_factory=list)
    content_units: int = 0
    body_text: str = ""
    hreflang: list[dict[str, str]] = field(default_factory=list)
    list_count: int = 0
    table_count: int = 0
    blockquote_count: int = 0
    wordpress: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanReport:
    documents: list[Document]
    findings: list[Finding]

    @property
    def summary(self) -> dict[str, int]:
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        counts["documents"] = len(self.documents)
        counts["findings"] = len(self.findings)
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "documents": [
                {
                    "source": document.source,
                    "input_format": document.input_format,
                    "content_units": document.content_units,
                    "schema_count": len(document.schemas),
                }
                for document in self.documents
            ],
        }

"""Public scanning API."""

from __future__ import annotations

from pathlib import Path

from .config import CheckerConfig
from .models import ScanReport
from .parsers import detect_format, parse_document
from .rules import evaluate


def scan_text(
    text: str,
    *,
    source: str = "<memory>",
    input_format: str = "auto",
    config: CheckerConfig | None = None,
) -> ScanReport:
    config = config or CheckerConfig()
    resolved_format = detect_format(source, text, input_format)
    document = parse_document(source, text, resolved_format)
    return ScanReport([document], evaluate(document, config))


def scan_path(
    path: str | Path,
    *,
    input_format: str = "auto",
    config: CheckerConfig | None = None,
) -> ScanReport:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return scan_text(
        text,
        source=str(file_path),
        input_format=input_format,
        config=config,
    )

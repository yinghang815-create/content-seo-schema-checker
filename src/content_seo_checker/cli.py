"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import CheckerConfig
from .models import Finding, ScanReport, Severity
from .parsers import SUPPORTED_SUFFIXES
from .reporters import render_console, render_json, render_sarif
from .scanner import scan_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo-schema-check",
        description="Run pre-publish SEO and JSON-LD schema quality gates.",
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument(
        "--input-format",
        choices=("auto", "html", "markdown", "wordpress", "jsonld"),
        default="auto",
    )
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument(
        "--report", choices=("console", "json", "sarif"), default="console"
    )
    parser.add_argument("--output", help="Write the report to a file")
    parser.add_argument(
        "--fail-on", choices=("error", "warning", "never"), default="error"
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = CheckerConfig.from_path(args.config)
        files = _expand_paths(args.paths)
        if not files:
            raise ValueError("no supported files were found")
        documents = []
        findings: list[Finding] = []
        for file_path in files:
            try:
                report = scan_path(
                    file_path, input_format=args.input_format, config=config
                )
                documents.extend(report.documents)
                findings.extend(report.findings)
            except (OSError, UnicodeError, TypeError, ValueError) as exc:
                findings.append(
                    Finding(
                        "input.parse_failed",
                        Severity.ERROR,
                        str(exc),
                        str(file_path),
                    )
                )
        combined = ScanReport(documents, findings)
        rendered = {
            "console": render_console,
            "json": render_json,
            "sarif": render_sarif,
        }[args.report](combined)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return _exit_code(combined, args.fail_on)
    except (OSError, TypeError, ValueError) as exc:
        print(f"seo-schema-check: {exc}", file=sys.stderr)
        return 2


def _expand_paths(values: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )
        else:
            raise ValueError(f"path does not exist: {path}")
    return sorted(set(files))


def _exit_code(report: ScanReport, fail_on: str) -> int:
    if fail_on == "never":
        return 0
    if any(finding.severity is Severity.ERROR for finding in report.findings):
        return 1
    if fail_on == "warning" and any(
        finding.severity is Severity.WARNING for finding in report.findings
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

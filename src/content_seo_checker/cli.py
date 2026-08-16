"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import CheckerConfig
from .geo import evaluate_geo
from .hreflang import check_hreflang
from .jsonld_diff import compare_jsonld
from .models import Finding, ScanReport, Severity
from .parsers import SUPPORTED_SUFFIXES, detect_format, parse_document
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
    values = list(argv) if argv is not None else sys.argv[1:]
    if values and values[0] == "scan":
        return _scan_main(values[1:])
    if values and values[0] == "jsonld-diff":
        return _jsonld_diff_main(values[1:])
    if values and values[0] == "hreflang-canonical":
        return _hreflang_main(values[1:])
    if values and values[0] == "geo-content":
        return _geo_main(values[1:])
    return _scan_main(values)


def _scan_main(argv: Sequence[str]) -> int:
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
        return _report(
            ScanReport(documents, findings), args.report, args.output, args.fail_on
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"seo-schema-check: {exc}", file=sys.stderr)
        return 2


def _report(
    report: ScanReport, report_format: str, output: str | None, fail_on: str
) -> int:
    rendered = {
        "console": render_console,
        "json": render_json,
        "sarif": render_sarif,
    }[report_format](report)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return _exit_code(report, fail_on)


def _advanced_report_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--report", choices=("console", "json", "sarif"), default="console"
    )
    parser.add_argument("--output")
    parser.add_argument(
        "--fail-on", choices=("error", "warning", "never"), default="error"
    )


def _load_document(path: Path, input_format: str = "auto"):
    text = path.read_text(encoding="utf-8")
    return parse_document(str(path), text, detect_format(path, text, input_format))


def _jsonld_diff_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="seo-schema-check jsonld-diff",
        description="Detect breaking semantic changes between two JSON-LD or content files.",
    )
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument(
        "--input-format",
        choices=("auto", "html", "markdown", "wordpress", "jsonld"),
        default="auto",
    )
    _advanced_report_arguments(parser)
    args = parser.parse_args(argv)
    try:
        baseline_path = Path(args.baseline)
        candidate_path = Path(args.candidate)
        baseline = _load_document(baseline_path, args.input_format)
        candidate = _load_document(candidate_path, args.input_format)
        findings = compare_jsonld(
            baseline.schemas, candidate.schemas, source=str(candidate_path)
        )
        return _report(
            ScanReport([baseline, candidate], findings),
            args.report,
            args.output,
            args.fail_on,
        )
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"seo-schema-check jsonld-diff: {exc}", file=sys.stderr)
        return 2


def _hreflang_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="seo-schema-check hreflang-canonical",
        description="Validate hreflang URL, canonical, self-reference, and reciprocal-link consistency.",
    )
    parser.add_argument("paths", nargs="+")
    _advanced_report_arguments(parser)
    args = parser.parse_args(argv)
    try:
        files = _expand_paths(args.paths)
        documents = [_load_document(path) for path in files]
        return _report(
            ScanReport(documents, check_hreflang(documents)),
            args.report,
            args.output,
            args.fail_on,
        )
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"seo-schema-check hreflang-canonical: {exc}", file=sys.stderr)
        return 2


def _geo_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="seo-schema-check geo-content",
        description="Audit source, entity, freshness, answer structure, and citation readiness.",
    )
    parser.add_argument("paths", nargs="+")
    parser.add_argument(
        "--input-format",
        choices=("auto", "html", "markdown", "wordpress"),
        default="auto",
    )
    _advanced_report_arguments(parser)
    args = parser.parse_args(argv)
    try:
        files = _expand_paths(args.paths)
        documents = [_load_document(path, args.input_format) for path in files]
        findings = [
            finding for document in documents for finding in evaluate_geo(document)
        ]
        return _report(
            ScanReport(documents, findings), args.report, args.output, args.fail_on
        )
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"seo-schema-check geo-content: {exc}", file=sys.stderr)
        return 2


def jsonld_diff_entry() -> int:
    return _jsonld_diff_main(sys.argv[1:])


def hreflang_entry() -> int:
    return _hreflang_main(sys.argv[1:])


def geo_content_entry() -> int:
    return _geo_main(sys.argv[1:])


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

"""Console, JSON, and SARIF report rendering."""

from __future__ import annotations

import json
from typing import Any

from .models import ScanReport, Severity


def render_console(report: ScanReport) -> str:
    lines: list[str] = []
    for finding in report.findings:
        location = finding.source
        if finding.line is not None:
            location += f":{finding.line}"
        lines.append(
            f"[{finding.severity.value.upper():7}] {finding.rule_id} {location}\n"
            f"          {finding.message}"
        )
        if finding.suggestion:
            lines.append(f"          Fix: {finding.suggestion}")
    summary = report.summary
    lines.append(
        f"Checked {summary['documents']} document(s): "
        f"{summary['error']} error(s), {summary['warning']} warning(s), "
        f"{summary['info']} info."
    )
    return "\n".join(lines)


def render_json(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def render_sarif(report: ScanReport) -> str:
    rule_ids = sorted({finding.rule_id for finding in report.findings})
    rules = [
        {
            "id": rule_id,
            "name": rule_id.replace(".", "_"),
            "shortDescription": {"text": rule_id.replace("_", " ")},
        }
        for rule_id in rule_ids
    ]
    results: list[dict[str, Any]] = []
    levels = {
        Severity.ERROR: "error",
        Severity.WARNING: "warning",
        Severity.INFO: "note",
    }
    for finding in report.findings:
        result: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": levels[finding.severity],
            "message": {"text": finding.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.source.replace("\\", "/")}
                    }
                }
            ],
        }
        if finding.line is not None:
            result["locations"][0]["physicalLocation"]["region"] = {
                "startLine": finding.line
            }
        results.append(result)
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Content SEO Schema Checker",
                        "informationUri": "https://github.com/yinghang815-create/content-seo-schema-checker",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2, sort_keys=True)

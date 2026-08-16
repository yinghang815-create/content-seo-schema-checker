"""Deterministic generative-engine content readiness checks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from .models import Document, Finding, Severity

SUMMARY_HEADING = re.compile(
    r"(?:summary|key takeaways|at a glance|bottom line|executive summary|摘要|要点|结论|速览)",
    re.IGNORECASE,
)
QUESTION_HEADING = re.compile(
    r"(?:\?|^(?:how|what|why|when|where|which|who|can|should|does|is|are)\b|如何|什么|为什么|是否|哪些|怎样)",
    re.IGNORECASE,
)
NUMERIC_CLAIM = re.compile(r"(?:\b\d+(?:\.\d+)?%|\b(?:19|20)\d{2}\b)")


def _schema_nodes(values: Iterable[Any]) -> Iterable[dict[str, Any]]:
    for value in values:
        if isinstance(value, list):
            yield from _schema_nodes(value)
        elif isinstance(value, dict):
            graph = value.get("@graph")
            if isinstance(graph, list):
                yield from _schema_nodes(graph)
            else:
                yield value


def _external_sources(document: Document) -> list[str]:
    canonical_host = urlparse(document.canonical or "").netloc.lower()
    sources: list[str] = []
    for link in document.links:
        href = str(link.get("href") or "")
        parsed = urlparse(href)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.netloc
            and (not canonical_host or parsed.netloc.lower() != canonical_host)
        ):
            sources.append(href)
    return sources


def evaluate_geo(document: Document) -> list[Finding]:
    findings: list[Finding] = []
    headings = [text for _, text, _ in document.headings]
    subheadings = [text for level, text, _ in document.headings if level >= 2]
    schemas = list(_schema_nodes(document.schemas))
    sources = _external_sources(document)

    if not any(SUMMARY_HEADING.search(heading) for heading in headings):
        findings.append(
            Finding(
                "geo.summary_missing",
                Severity.WARNING,
                "no summary, key-takeaways, or conclusion section was found",
                document.source,
                suggestion="Add a concise answer-first summary that can stand alone when cited.",
            )
        )
    if document.content_units >= 300 and len(subheadings) < 3:
        findings.append(
            Finding(
                "geo.sectioning_weak",
                Severity.WARNING,
                "long content has fewer than three descriptive subheadings",
                document.source,
                suggestion="Split the decision path into specific, descriptive sections.",
            )
        )
    if document.list_count + document.table_count + document.blockquote_count == 0:
        findings.append(
            Finding(
                "geo.citable_structure_missing",
                Severity.WARNING,
                "no list, table, or blockquote was found",
                document.source,
                suggestion="Add a compact checklist, comparison table, or attributed evidence block.",
            )
        )
    if not sources:
        findings.append(
            Finding(
                "geo.sources_missing",
                Severity.WARNING,
                "no external source links were found",
                document.source,
                suggestion="Cite primary or authoritative sources for verifiable claims.",
            )
        )
    if NUMERIC_CLAIM.search(document.body_text) and not sources:
        findings.append(
            Finding(
                "geo.numeric_claim_unsourced",
                Severity.ERROR,
                "numeric or dated claims appear without an external source",
                document.source,
                suggestion="Attach a nearby primary-source citation to each material numeric claim.",
            )
        )
    has_author = bool(document.meta.get("author")) or any(
        node.get("author") for node in schemas
    )
    if not has_author:
        findings.append(
            Finding(
                "geo.author_missing",
                Severity.WARNING,
                "no author entity was found in metadata or JSON-LD",
                document.source,
                suggestion="Identify the author or reviewing organization in Article schema.",
            )
        )
    has_freshness = bool(document.meta.get("article:modified_time")) or any(
        node.get("dateModified") or node.get("datePublished") for node in schemas
    )
    if not has_freshness:
        findings.append(
            Finding(
                "geo.freshness_missing",
                Severity.WARNING,
                "no publication or modification date was found",
                document.source,
                suggestion="Expose datePublished and dateModified in visible content and JSON-LD.",
            )
        )
    if not any(QUESTION_HEADING.search(heading) for heading in subheadings):
        findings.append(
            Finding(
                "geo.question_section_missing",
                Severity.INFO,
                "no question-led section heading was found",
                document.source,
                suggestion="Answer at least one concrete user question in a dedicated section.",
            )
        )
    return findings

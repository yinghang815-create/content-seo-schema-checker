"""SEO and structured-data rules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from .config import CheckerConfig
from .models import Document, Finding, Severity

SCHEMA_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "Article": (
        "headline",
        "image",
        "author",
        "datePublished",
        "dateModified",
        "mainEntityOfPage",
    ),
    "BlogPosting": (
        "headline",
        "image",
        "author",
        "datePublished",
        "dateModified",
        "mainEntityOfPage",
    ),
    "NewsArticle": (
        "headline",
        "image",
        "author",
        "datePublished",
        "dateModified",
        "mainEntityOfPage",
    ),
    "Product": ("name", "image", "description", "offers"),
    "FAQPage": ("mainEntity",),
    "BreadcrumbList": ("itemListElement",),
    "Organization": ("name", "url"),
}


def evaluate(document: Document, config: CheckerConfig) -> list[Finding]:
    findings: list[Finding] = []

    def add(
        rule_id: str,
        severity: Severity,
        message: str,
        *,
        suggestion: str | None = None,
        evidence: str | None = None,
        line: int | None = None,
    ) -> None:
        if config.is_enabled(rule_id):
            findings.append(
                Finding(
                    rule_id,
                    config.severity(rule_id, severity),
                    message,
                    document.source,
                    suggestion,
                    evidence,
                    line,
                )
            )

    if document.input_format != "jsonld":
        _check_content(document, config, add)
    _check_schema(document, config, add)
    if document.input_format == "wordpress":
        _check_wordpress(document, add)
    return findings


def _check_content(document: Document, config: CheckerConfig, add: Any) -> None:
    title = document.title or ""
    description = document.description or ""
    if not title:
        add(
            "title.missing",
            Severity.ERROR,
            "SEO title is missing.",
            suggestion="Add a unique page title.",
        )
    elif len(title) < config.thresholds["title_min"]:
        add(
            "title.too_short",
            Severity.WARNING,
            f"SEO title has {len(title)} characters; target at least {config.thresholds['title_min']}.",
            evidence=title,
        )
    elif len(title) > config.thresholds["title_max"]:
        add(
            "title.too_long",
            Severity.WARNING,
            f"SEO title has {len(title)} characters; target at most {config.thresholds['title_max']}.",
            evidence=title,
        )

    if not description:
        add(
            "description.missing",
            Severity.ERROR,
            "Meta description is missing.",
            suggestion="Add a concise search-result description.",
        )
    elif len(description) < config.thresholds["description_min"]:
        add(
            "description.too_short",
            Severity.WARNING,
            f"Meta description has {len(description)} characters; target at least {config.thresholds['description_min']}.",
            evidence=description,
        )
    elif len(description) > config.thresholds["description_max"]:
        add(
            "description.too_long",
            Severity.WARNING,
            f"Meta description has {len(description)} characters; target at most {config.thresholds['description_max']}.",
            evidence=description,
        )

    if not document.canonical:
        add("canonical.missing", Severity.WARNING, "Canonical URL is missing.")
    else:
        parsed = urlparse(document.canonical)
        if not parsed.scheme or not parsed.netloc:
            add(
                "canonical.not_absolute",
                Severity.ERROR,
                "Canonical URL must be absolute.",
                evidence=document.canonical,
            )
        elif parsed.scheme != "https":
            add(
                "canonical.not_https",
                Severity.WARNING,
                "Canonical URL should use HTTPS.",
                evidence=document.canonical,
            )

    if any(item in {"noindex", "none"} for item in document.robots):
        add(
            "robots.noindex",
            Severity.ERROR,
            "Robots directives prevent indexing.",
            evidence=", ".join(document.robots),
        )
    if not document.lang:
        add("html.lang_missing", Severity.WARNING, "Document language is missing.")

    h1s = [(text, line) for level, text, line in document.headings if level == 1]
    if not h1s:
        add("heading.h1_missing", Severity.ERROR, "No H1 heading was found.")
    elif len(h1s) > 1:
        add(
            "heading.multiple_h1",
            Severity.ERROR,
            f"Found {len(h1s)} H1 headings; expected one.",
        )
    previous_level: int | None = None
    for level, text, line in document.headings:
        if previous_level is not None and level > previous_level + 1:
            add(
                "heading.level_skipped",
                Severity.WARNING,
                f"Heading level jumps from H{previous_level} to H{level}.",
                evidence=text,
                line=line,
            )
        previous_level = level

    if document.content_units < config.thresholds["content_units_min"]:
        add(
            "content.too_thin",
            Severity.WARNING,
            f"Content has {document.content_units} word/CJK-character units; target at least {config.thresholds['content_units_min']}.",
        )

    missing_alt = [image for image in document.images if image.get("alt") is None]
    if missing_alt:
        add(
            "image.alt_missing",
            Severity.ERROR,
            f"{len(missing_alt)} image(s) are missing an alt attribute.",
            line=missing_alt[0].get("line"),
        )
    empty_links = [
        link for link in document.links if not str(link.get("href") or "").strip()
    ]
    if empty_links:
        add(
            "link.href_missing",
            Severity.WARNING,
            f"{len(empty_links)} link(s) have an empty href.",
            line=empty_links[0].get("line"),
        )

    for key, label in (
        ("og:title", "Open Graph title"),
        ("og:description", "Open Graph description"),
        ("og:image", "Open Graph image"),
        ("twitter:card", "Twitter card"),
    ):
        if not document.meta.get(key):
            add(
                f"social.{key.replace(':', '_')}_missing",
                Severity.WARNING,
                f"{label} is missing.",
            )


def _check_schema(document: Document, config: CheckerConfig, add: Any) -> None:
    for error in document.schema_errors:
        add("schema.invalid_json", Severity.ERROR, error)
    if not document.schemas:
        add("schema.missing", Severity.ERROR, "No JSON-LD structured data was found.")
        return

    nodes = list(_schema_nodes(document.schemas))
    seen_types: set[str] = set()
    for node in nodes:
        context = node.get("@context")
        if context is None:
            add(
                "schema.context_missing",
                Severity.ERROR,
                "Schema node is missing @context.",
                evidence=str(node.get("@type") or "unknown"),
            )
        elif isinstance(context, str) and "schema.org" not in context.lower():
            add(
                "schema.context_invalid",
                Severity.WARNING,
                "Schema @context does not reference schema.org.",
                evidence=context,
            )
        raw_types = node.get("@type")
        types = (
            raw_types
            if isinstance(raw_types, list)
            else [raw_types]
            if raw_types
            else []
        )
        if not types:
            add("schema.type_missing", Severity.ERROR, "Schema node is missing @type.")
        for schema_type in (str(item) for item in types):
            seen_types.add(schema_type)
            requirements = SCHEMA_REQUIREMENTS.get(schema_type, ())
            missing = [
                key for key in requirements if node.get(key) in (None, "", [], {})
            ]
            if missing:
                add(
                    f"schema.{schema_type.lower()}.properties_missing",
                    Severity.ERROR,
                    f"{schema_type} is missing required/recommended properties: {', '.join(missing)}.",
                    evidence=str(
                        node.get("@id")
                        or node.get("headline")
                        or node.get("name")
                        or schema_type
                    ),
                )
    for required_type in config.required_schema_types:
        if required_type not in seen_types:
            add(
                "schema.required_type_missing",
                Severity.ERROR,
                f"Required schema type {required_type} was not found.",
            )


def _check_wordpress(document: Document, add: Any) -> None:
    if not str(document.wordpress.get("slug") or "").strip():
        add("wordpress.slug_missing", Severity.ERROR, "WordPress slug is missing.")
    featured = document.wordpress.get("featured_media")
    if featured in (None, 0, "0", ""):
        add(
            "wordpress.featured_media_missing",
            Severity.WARNING,
            "WordPress featured media is missing.",
        )


def _schema_nodes(values: Iterable[Any]) -> Iterable[dict[str, Any]]:
    for value in values:
        if isinstance(value, list):
            yield from _schema_nodes(value)
        elif isinstance(value, dict):
            graph = value.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        if "@context" not in item and "@context" in value:
                            item = {"@context": value["@context"], **item}
                        yield item
            else:
                yield value

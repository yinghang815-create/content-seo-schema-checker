"""Cross-page hreflang and canonical consistency checks."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from .models import Document, Finding, Severity

LANGUAGE = re.compile(r"^(?:x-default|[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)$")


def _normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, "")
    )


def check_hreflang(documents: list[Document]) -> list[Finding]:
    findings: list[Finding] = []
    by_canonical = {
        _normalize_url(document.canonical): document
        for document in documents
        if document.canonical
    }

    for document in documents:
        if not document.canonical:
            findings.append(
                Finding(
                    "hreflang.canonical_missing",
                    Severity.ERROR,
                    "hreflang validation requires a canonical URL",
                    document.source,
                )
            )
        seen_languages: set[str] = set()
        normalized_links: set[str] = set()
        for entry in document.hreflang:
            language = entry.get("lang", "").strip()
            href = entry.get("href", "").strip()
            normalized_language = language.lower()
            if not LANGUAGE.fullmatch(language):
                findings.append(
                    Finding(
                        "hreflang.language_invalid",
                        Severity.ERROR,
                        f"invalid hreflang language code: {language or '<empty>'}",
                        document.source,
                        evidence=language,
                    )
                )
            if normalized_language in seen_languages:
                findings.append(
                    Finding(
                        "hreflang.language_duplicate",
                        Severity.ERROR,
                        f"duplicate hreflang language: {language}",
                        document.source,
                        evidence=language,
                    )
                )
            seen_languages.add(normalized_language)
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                findings.append(
                    Finding(
                        "hreflang.url_not_absolute",
                        Severity.ERROR,
                        f"hreflang URL must be absolute: {href or '<empty>'}",
                        document.source,
                        evidence=href,
                    )
                )
                continue
            if parsed.scheme != "https":
                findings.append(
                    Finding(
                        "hreflang.url_not_https",
                        Severity.WARNING,
                        f"hreflang URL is not HTTPS: {href}",
                        document.source,
                        evidence=href,
                    )
                )
            if parsed.fragment:
                findings.append(
                    Finding(
                        "hreflang.url_has_fragment",
                        Severity.WARNING,
                        f"hreflang URL contains a fragment: {href}",
                        document.source,
                        evidence=href,
                    )
                )
            normalized_links.add(_normalize_url(href))

        if document.hreflang and document.canonical:
            canonical = _normalize_url(document.canonical)
            if canonical not in normalized_links:
                findings.append(
                    Finding(
                        "hreflang.self_reference_missing",
                        Severity.WARNING,
                        "hreflang cluster does not include the page's canonical URL",
                        document.source,
                        evidence=document.canonical,
                    )
                )

        source_canonical = (
            _normalize_url(document.canonical) if document.canonical else None
        )
        if source_canonical:
            for target_url in sorted(normalized_links):
                target = by_canonical.get(target_url)
                if target is None or target is document:
                    continue
                reciprocal = {
                    _normalize_url(entry["href"])
                    for entry in target.hreflang
                    if entry.get("href") and urlparse(entry["href"]).netloc
                }
                if source_canonical not in reciprocal:
                    findings.append(
                        Finding(
                            "hreflang.return_link_missing",
                            Severity.ERROR,
                            f"alternate page does not link back from {target_url}",
                            document.source,
                            evidence=target.source,
                        )
                    )
    return findings

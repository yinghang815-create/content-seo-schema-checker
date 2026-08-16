"""Input parsers for HTML, Markdown, WordPress payloads, and JSON-LD."""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .models import Document

SUPPORTED_SUFFIXES = {".html", ".htm", ".md", ".markdown", ".json"}


class _ContentHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.heading_level: int | None = None
        self.heading_line: int | None = None
        self.heading_parts: list[str] = []
        self.lang: str | None = None
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.hreflang: list[dict[str, str]] = []
        self.images: list[dict[str, Any]] = []
        self.links: list[dict[str, Any]] = []
        self.headings: list[tuple[int, str, int | None]] = []
        self.schemas: list[Any] = []
        self.schema_errors: list[str] = []
        self.text_parts: list[str] = []
        self.list_count = 0
        self.table_count = 0
        self.blockquote_count = 0
        self._ignored_depth = 0
        self._schema_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value for key, value in attrs}
        line = self.getpos()[0]
        if tag == "html":
            self.lang = attributes.get("lang")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (attributes.get("name") or attributes.get("property") or "").lower()
            value = attributes.get("content")
            if key and value is not None:
                self.meta[key] = value.strip()
        elif tag == "link":
            rel = (attributes.get("rel") or "").lower().split()
            if "canonical" in rel:
                self.canonical = attributes.get("href")
            if (
                "alternate" in rel
                and attributes.get("hreflang")
                and attributes.get("href")
            ):
                self.hreflang.append(
                    {
                        "lang": str(attributes["hreflang"]).strip(),
                        "href": str(attributes["href"]).strip(),
                    }
                )
        elif tag in {f"h{level}" for level in range(1, 7)}:
            self.heading_level = int(tag[1])
            self.heading_line = line
            self.heading_parts = []
        elif tag == "img":
            self.images.append(
                {
                    "src": attributes.get("src"),
                    "alt": attributes.get("alt"),
                    "line": line,
                }
            )
        elif tag == "a":
            self.links.append({"href": attributes.get("href"), "line": line})
        if tag in {"ol", "ul"}:
            self.list_count += 1
        elif tag == "table":
            self.table_count += 1
        elif tag == "blockquote":
            self.blockquote_count += 1
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if (
            tag == "script"
            and (attributes.get("type") or "").lower() == "application/ld+json"
        ):
            self._schema_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif self.heading_level is not None and tag == f"h{self.heading_level}":
            text = _clean_text(" ".join(self.heading_parts))
            self.headings.append((self.heading_level, text, self.heading_line))
            self.heading_level = None
            self.heading_line = None
            self.heading_parts = []
        if tag == "script" and self._schema_parts is not None:
            raw = "".join(self._schema_parts).strip()
            if raw:
                try:
                    value = json.loads(raw)
                    if isinstance(value, list):
                        self.schemas.extend(value)
                    else:
                        self.schemas.append(value)
                except json.JSONDecodeError as exc:
                    self.schema_errors.append(
                        f"invalid JSON-LD at line {exc.lineno}: {exc.msg}"
                    )
            self._schema_parts = None
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._schema_parts is not None:
            self._schema_parts.append(data)
        if self.in_title:
            self.title_parts.append(data)
        if self.heading_level is not None:
            self.heading_parts.append(data)
        if self._ignored_depth == 0 and not self.in_title:
            self.text_parts.append(data)


def detect_format(path: str | Path, text: str, explicit: str = "auto") -> str:
    if explicit != "auto":
        return explicit
    suffix = Path(path).suffix.lower()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        parsed = json.loads(text)
        if isinstance(parsed, dict) and any(
            key in parsed
            for key in ("content", "slug", "featured_media", "yoast_head_json")
        ):
            return "wordpress"
        return "jsonld"
    stripped = text.lstrip()
    if stripped.startswith("<"):
        return "html"
    if stripped.startswith(("{", "[")):
        return "jsonld"
    return "markdown"


def parse_document(source: str, text: str, input_format: str) -> Document:
    if input_format == "html":
        return _parse_html(source, text, "html")
    if input_format == "markdown":
        return _parse_markdown(source, text)
    if input_format == "wordpress":
        return _parse_wordpress(source, text)
    if input_format == "jsonld":
        return _parse_jsonld(source, text)
    raise ValueError(f"unsupported input format: {input_format}")


def _parse_html(source: str, text: str, input_format: str) -> Document:
    parser = _ContentHTMLParser()
    parser.feed(text)
    robots = [
        item.strip().lower()
        for item in parser.meta.get("robots", "").split(",")
        if item.strip()
    ]
    return Document(
        source=source,
        input_format=input_format,
        title=_optional_text(" ".join(parser.title_parts)),
        description=_optional_text(parser.meta.get("description")),
        canonical=_optional_text(parser.canonical),
        robots=robots,
        lang=_optional_text(parser.lang),
        headings=parser.headings,
        images=parser.images,
        links=parser.links,
        meta=parser.meta,
        schemas=parser.schemas,
        schema_errors=parser.schema_errors,
        content_units=_content_units(" ".join(parser.text_parts)),
        body_text=_clean_text(" ".join(parser.text_parts)),
        hreflang=parser.hreflang,
        list_count=parser.list_count,
        table_count=parser.table_count,
        blockquote_count=parser.blockquote_count,
    )


def _parse_markdown(source: str, text: str) -> Document:
    front_matter, body, body_start = _front_matter(text)
    headings: list[tuple[int, str, int | None]] = []
    for index, line in enumerate(body.splitlines(), start=body_start):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((len(match.group(1)), _clean_text(match.group(2)), index))
    images = [
        {"alt": match.group(1), "src": match.group(2), "line": None}
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", body)
    ]
    links = [
        {"href": match.group(2), "line": None}
        for match in re.finditer(r"(?<!!)\[([^\]]+)\]\(([^)]*)\)", body)
    ]
    embedded = _parse_html(source, body, "markdown")
    schemas = list(embedded.schemas)
    schema_errors = list(embedded.schema_errors)
    for key in ("schema", "json_ld", "json-ld"):
        value = front_matter.get(key)
        if value is not None:
            if isinstance(value, list):
                schemas.extend(value)
            else:
                schemas.append(value)
    title = _first(front_matter, "seo_title", "title")
    if title is None:
        title = next((text for level, text, _ in headings if level == 1), None)
    description = _first(front_matter, "description", "seo_description", "excerpt")
    meta: dict[str, str] = {}
    for key, value in front_matter.items():
        normalized = (
            str(key).lower().replace("og_", "og:").replace("twitter_", "twitter:")
        )
        if normalized.startswith(("og:", "twitter:")):
            meta[normalized] = str(value)
    robots_value = front_matter.get("robots", "")
    robots = (
        [str(item).lower() for item in robots_value]
        if isinstance(robots_value, list)
        else [
            item.strip().lower()
            for item in str(robots_value).split(",")
            if item.strip()
        ]
    )
    plain = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    plain = re.sub(r"`[^`]*`", " ", plain)
    plain = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", plain)
    plain = re.sub(r"[#>*_~-]", " ", plain)
    hreflang = _front_matter_hreflang(front_matter.get("hreflang"))
    list_count = sum(
        1 for line in body.splitlines() if re.match(r"^\s*(?:[-+*]|\d+\.)\s+", line)
    )
    table_count = sum(
        1 for line in body.splitlines() if re.match(r"^\s*\|?.+\|.+\|?\s*$", line)
    )
    blockquote_count = sum(
        1 for line in body.splitlines() if re.match(r"^\s*>\s+", line)
    )
    return Document(
        source=source,
        input_format="markdown",
        title=_optional_text(title),
        description=_optional_text(description),
        canonical=_optional_text(_first(front_matter, "canonical", "canonical_url")),
        robots=robots,
        lang=_optional_text(_first(front_matter, "lang", "language")),
        headings=headings,
        images=images + embedded.images,
        links=links + embedded.links,
        meta=meta,
        schemas=schemas,
        schema_errors=schema_errors,
        content_units=_content_units(plain),
        body_text=_clean_text(plain),
        hreflang=hreflang + embedded.hreflang,
        list_count=list_count + embedded.list_count,
        table_count=table_count + embedded.table_count,
        blockquote_count=blockquote_count + embedded.blockquote_count,
    )


def _parse_wordpress(source: str, text: str) -> Document:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise TypeError("WordPress payload must be a JSON object")
    content = _rendered(payload.get("content"))
    yoast_head = _rendered(payload.get("yoast_head"))
    document = _parse_html(source, f"{yoast_head}\n{content}", "wordpress")
    yoast = payload.get("yoast_head_json")
    if not isinstance(yoast, dict):
        yoast = {}
    document.title = _optional_text(
        yoast.get("title") or _rendered(payload.get("title")) or document.title
    )
    document.description = _optional_text(
        yoast.get("description")
        or _strip_html(_rendered(payload.get("excerpt")))
        or document.description
    )
    document.canonical = _optional_text(yoast.get("canonical") or document.canonical)
    robots = yoast.get("robots")
    if isinstance(robots, dict):
        document.robots = [
            str(value).lower() for value in robots.values() if isinstance(value, str)
        ]
    for source_key, target_key in (
        ("og_title", "og:title"),
        ("og_description", "og:description"),
        ("og_url", "og:url"),
        ("twitter_card", "twitter:card"),
        ("twitter_title", "twitter:title"),
        ("twitter_description", "twitter:description"),
    ):
        if yoast.get(source_key):
            document.meta[target_key] = str(yoast[source_key])
    og_image = yoast.get("og_image")
    if (
        isinstance(og_image, list)
        and og_image
        and isinstance(og_image[0], dict)
        and og_image[0].get("url")
    ):
        document.meta["og:image"] = str(og_image[0]["url"])
    schema = yoast.get("schema")
    if isinstance(schema, dict):
        document.schemas.append(schema)
    document.wordpress = {
        "slug": payload.get("slug"),
        "status": payload.get("status"),
        "featured_media": payload.get("featured_media"),
        "type": payload.get("type"),
    }
    return document


def _parse_jsonld(source: str, text: str) -> Document:
    value = json.loads(text)
    schemas = value if isinstance(value, list) else [value]
    return Document(source=source, input_format="jsonld", schemas=schemas)


def _front_matter(text: str) -> tuple[dict[str, Any], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 1
    try:
        end = next(
            index for index in range(1, len(lines)) if lines[index].strip() == "---"
        )
    except StopIteration:
        return {}, text, 1
    values: dict[str, Any] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _scalar(raw_value.strip())
    return values, "\n".join(lines[end + 1 :]), end + 2


def _scalar(value: str) -> Any:
    if not value:
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip("'\"")


def _rendered(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("rendered") or value.get("raw") or "")
    return str(value or "")


def _front_matter_hreflang(value: Any) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if isinstance(value, dict):
        entries.extend(
            {"lang": str(language), "href": str(href)}
            for language, href in value.items()
            if href
        )
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("lang") and item.get("href"):
                entries.append({"lang": str(item["lang"]), "href": str(item["href"])})
    return entries


def _strip_html(value: str) -> str:
    return _clean_text(re.sub(r"<[^>]+>", " ", value))


def _first(values: dict[str, Any], *keys: str) -> Any:
    return next(
        (values[key] for key in keys if values.get(key) not in (None, "")), None
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _clean_text(str(value))
    return cleaned or None


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _content_units(value: str) -> int:
    cleaned = _clean_text(value)
    latin_words = re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", cleaned)
    cjk_characters = re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", cleaned)
    return len(latin_words) + len(cjk_characters)

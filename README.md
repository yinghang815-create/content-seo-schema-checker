# Content SEO Schema Checker

[![CI](https://github.com/yinghang815-create/content-seo-schema-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/yinghang815-create/content-seo-schema-checker/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Content SEO Schema Checker is a dependency-free pre-publish quality gate for
website content. It audits search metadata, page structure, social previews,
images, links, WordPress fields, and JSON-LD structured data before a page goes
live.

It scans local HTML, Markdown with front matter, WordPress REST API payloads,
and standalone JSON-LD. Reports are available as readable terminal output,
JSON, or SARIF for GitHub Code Scanning.

## Why run checks before publication?

Browser-based SEO tools usually inspect a page after deployment. At that point,
a missing canonical, `noindex`, invalid Article schema, or empty featured image
has already reached production. This tool moves deterministic checks into the
editorial and release workflow.

Typical uses include:

- checking generated HTML before deployment;
- validating Markdown content in a pull request;
- auditing WordPress REST payloads before changing status to `publish`;
- verifying JSON-LD property completeness;
- enforcing the same SEO rules locally and in CI;
- uploading SARIF findings to GitHub Code Scanning.

## Quick start

Python 3.10 or newer is required.

```bash
python -m pip install .
seo-schema-check path/to/page.html
```

Scan a directory recursively:

```bash
seo-schema-check content/ --fail-on warning
```

Create JSON and SARIF reports:

```bash
seo-schema-check content/ --report json --output seo-report.json
seo-schema-check content/ --report sarif --output seo-report.sarif
```

Validate a WordPress REST payload explicitly:

```bash
seo-schema-check draft-post.json --input-format wordpress
```

Exit codes are designed for automation:

- `0`: the selected quality gate passed;
- `1`: findings met the `--fail-on` threshold;
- `2`: configuration, path, or command error.

## Supported inputs

### HTML

The parser extracts the title, meta tags, canonical link, robots directives,
language, headings, images, links, visible content, and every
`application/ld+json` script.

### Markdown

Markdown checks read simple `key: value` front matter, headings, links, images,
embedded JSON-LD scripts, and multilingual content length. Recognized metadata
includes:

```yaml
---
title: A useful page title
description: A search-result description
canonical: https://example.com/guides/page
lang: en
robots: index,follow
og_title: Social title
og_description: Social description
og_image: https://example.com/hero.jpg
twitter_card: summary_large_image
schema: {"@context":"https://schema.org","@type":"Article"}
---
```

The built-in front-matter reader deliberately supports a small, portable
subset rather than a complete YAML implementation.

### WordPress REST JSON

WordPress payload checks understand string or `{ "raw": ... }` /
`{ "rendered": ... }` title, content, and excerpt fields. They also read
`slug`, `featured_media`, `status`, `yoast_head`, and `yoast_head_json`,
including Yoast social metadata and schema graphs.

### Standalone JSON-LD

A JSON object or array can be checked independently. Schema graphs using
`@graph` are expanded into individual nodes while inheriting their parent
`@context`.

## Rules

The default rules cover:

- SEO title and meta-description presence and length;
- absolute HTTPS canonical URLs;
- accidental `noindex` directives;
- document language and one H1;
- skipped heading levels;
- thin content, with CJK characters counted correctly;
- missing image `alt` attributes and empty link targets;
- Open Graph and Twitter card fields;
- valid JSON-LD, `@context`, and `@type`;
- recommended properties for Article, BlogPosting, NewsArticle, Product,
  FAQPage, BreadcrumbList, and Organization;
- WordPress slug and featured media.

See [docs/rules.md](docs/rules.md) for stable rule IDs and default severity.
This checker verifies deterministic source-level requirements; it does not
claim to replace Google's Rich Results Test or a search engine crawl.

## Configuration

Pass a JSON configuration file with `--config`:

```json
{
  "thresholds": {
    "title_min": 25,
    "title_max": 65,
    "description_min": 70,
    "description_max": 165,
    "content_units_min": 250
  },
  "required_schema_types": ["Article"],
  "disabled_rules": ["social.twitter_card_missing"],
  "severity_overrides": {
    "canonical.missing": "error"
  }
}
```

Unknown thresholds and invalid severity values fail closed instead of being
silently ignored. A complete example is in
[examples/checker-config.json](examples/checker-config.json).

## Python API

```python
from content_seo_checker import CheckerConfig, scan_path

config = CheckerConfig.from_path("seo-check.json")
report = scan_path("draft.html", config=config)

for finding in report.findings:
    print(finding.rule_id, finding.severity.value, finding.message)
```

## GitHub Actions and SARIF

Run the CLI in a workflow and upload the report with
`github/codeql-action/upload-sarif`. The repository's own CI runs the complete
unit suite on Windows and Ubuntu with the oldest and newest supported Python
versions.

SARIF output uses source paths and line numbers when the parser can identify
them, allowing findings to appear next to content changes.

## Development

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

The core package has no runtime dependencies. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before opening
a pull request or reporting a vulnerability.

## Status

Version 0.1.0 is an alpha release. Rule IDs are intended to remain stable, but
the configuration surface may evolve before 1.0.

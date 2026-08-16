from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from content_seo_checker import CheckerConfig, Severity, scan_text
from content_seo_checker.reporters import render_sarif


def good_html() -> str:
    body = " ".join(f"usefulword{index}" for index in range(320))
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "A Complete Pre-Publish SEO Checklist for Content Operations",
        "image": "https://example.com/hero.jpg",
        "author": {"@type": "Person", "name": "Editor"},
        "datePublished": "2026-08-16",
        "dateModified": "2026-08-16",
        "mainEntityOfPage": "https://example.com/guides/pre-publish-seo",
    }
    return f"""
    <html lang="en"><head>
      <title>Pre-Publish SEO Checks for Content Operations Teams</title>
      <meta name="description" content="Use this practical pre-publish checklist to validate search metadata, page structure, social previews, and structured data before content goes live.">
      <meta name="robots" content="index,follow">
      <meta property="og:title" content="Pre-Publish SEO Checks">
      <meta property="og:description" content="Validate content before launch">
      <meta property="og:image" content="https://example.com/hero.jpg">
      <meta name="twitter:card" content="summary_large_image">
      <link rel="canonical" href="https://example.com/guides/pre-publish-seo">
      <script type="application/ld+json">{json.dumps(schema)}</script>
    </head><body><h1>Pre-Publish SEO Checks</h1><h2>Metadata</h2>
      <img src="hero.jpg" alt="SEO checklist before publication"><p>{body}</p>
    </body></html>
    """


class RuleTests(unittest.TestCase):
    def test_complete_article_passes_without_errors(self) -> None:
        report = scan_text(good_html(), source="good.html", input_format="html")
        errors = [item for item in report.findings if item.severity is Severity.ERROR]
        self.assertEqual([], errors)

    def test_missing_basics_raise_stable_rule_ids(self) -> None:
        report = scan_text(
            "<html><body><h2>Skipped</h2><img src='x'></body></html>",
            source="bad.html",
            input_format="html",
        )
        rule_ids = {item.rule_id for item in report.findings}

        self.assertTrue(
            {
                "title.missing",
                "description.missing",
                "heading.h1_missing",
                "image.alt_missing",
                "schema.missing",
            }.issubset(rule_ids)
        )

    def test_article_schema_properties_are_checked(self) -> None:
        html = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Only headline"}</script>'
        report = scan_text(html, source="article.html", input_format="html")
        finding = next(
            item
            for item in report.findings
            if item.rule_id == "schema.article.properties_missing"
        )
        self.assertIn("datePublished", finding.message)
        self.assertIn("author", finding.message)

    def test_config_can_disable_and_override_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "disabled_rules": ["schema.missing"],
                        "severity_overrides": {"title.missing": "warning"},
                        "required_schema_types": ["FAQPage"],
                    }
                ),
                encoding="utf-8",
            )
            config = CheckerConfig.from_path(path)
        report = scan_text(
            "<h1>Page</h1>", source="page.html", input_format="html", config=config
        )

        self.assertNotIn("schema.missing", {item.rule_id for item in report.findings})
        title = next(
            item for item in report.findings if item.rule_id == "title.missing"
        )
        self.assertIs(Severity.WARNING, title.severity)

    def test_sarif_has_github_code_scanning_shape(self) -> None:
        report = scan_text("<h2>Page</h2>", source="page.html", input_format="html")
        sarif = json.loads(render_sarif(report))

        self.assertEqual("2.1.0", sarif["version"])
        self.assertEqual(
            "Content SEO Schema Checker", sarif["runs"][0]["tool"]["driver"]["name"]
        )
        self.assertGreater(len(sarif["runs"][0]["results"]), 0)


if __name__ == "__main__":
    unittest.main()

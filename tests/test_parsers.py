from __future__ import annotations

import json
import unittest

from content_seo_checker.parsers import detect_format, parse_document


class ParserTests(unittest.TestCase):
    def test_html_extracts_search_social_and_schema_fields(self) -> None:
        html = """
        <html lang="en"><head>
          <title>A useful title for import operations teams</title>
          <meta name="description" content="A detailed description that explains the page value to search users before they decide to open the result.">
          <meta property="og:title" content="Open graph title">
          <link rel="canonical" href="https://example.com/guide">
          <script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Guide"}</script>
        </head><body>
          <h1>Guide</h1><h2>Decision</h2>
          <img src="hero.jpg" alt="Importer reviewing a checklist">
          <a href="/next">Next</a><p>Useful body copy.</p>
        </body></html>
        """
        document = parse_document("guide.html", html, "html")

        self.assertEqual("en", document.lang)
        self.assertEqual("https://example.com/guide", document.canonical)
        self.assertEqual("Open graph title", document.meta["og:title"])
        self.assertEqual([(1, "Guide", 9), (2, "Decision", 9)], document.headings)
        self.assertEqual("Article", document.schemas[0]["@type"])
        self.assertGreater(document.content_units, 0)

    def test_invalid_json_ld_is_preserved_as_parse_error(self) -> None:
        document = parse_document(
            "bad.html",
            '<script type="application/ld+json">{"@type":</script>',
            "html",
        )
        self.assertEqual(1, len(document.schema_errors))
        self.assertIn("invalid JSON-LD", document.schema_errors[0])

    def test_markdown_front_matter_and_cjk_content(self) -> None:
        markdown = """---
title: Importer Compliance Guide for Regional Distribution Teams
description: A practical description for regional distributors evaluating compliance evidence before a product launch.
canonical: https://example.com/guides/compliance
lang: zh-CN
og_title: Importer Compliance Guide
twitter_card: summary_large_image
schema: {"@context":"https://schema.org","@type":"Article","headline":"Importer Compliance Guide"}
---
# Importer Compliance Guide

这是用于检查中文内容统计是否正确的正文。更多内容帮助进口商完成发布前检查。
"""
        document = parse_document("guide.md", markdown, "markdown")

        self.assertEqual("zh-CN", document.lang)
        self.assertEqual("Importer Compliance Guide", document.meta["og:title"])
        self.assertEqual("summary_large_image", document.meta["twitter:card"])
        self.assertGreater(document.content_units, 20)
        self.assertEqual("Article", document.schemas[0]["@type"])

    def test_wordpress_rest_payload_uses_yoast_fields(self) -> None:
        payload = {
            "title": {"rendered": "WordPress Distribution Guide"},
            "content": {"rendered": "<h1>Distribution Guide</h1><p>Body copy</p>"},
            "excerpt": {"rendered": "<p>Excerpt text</p>"},
            "slug": "distribution-guide",
            "featured_media": 42,
            "status": "draft",
            "yoast_head_json": {
                "title": "SEO title from Yoast",
                "description": "SEO description from Yoast",
                "canonical": "https://example.com/distribution-guide",
                "twitter_card": "summary_large_image",
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Distribution Guide",
                },
            },
        }
        document = parse_document("post.json", json.dumps(payload), "wordpress")

        self.assertEqual("SEO title from Yoast", document.title)
        self.assertEqual("SEO description from Yoast", document.description)
        self.assertEqual("distribution-guide", document.wordpress["slug"])
        self.assertEqual("Article", document.schemas[0]["@type"])

    def test_auto_detection(self) -> None:
        self.assertEqual("html", detect_format("page.html", "", "auto"))
        self.assertEqual("markdown", detect_format("page.md", "", "auto"))
        self.assertEqual(
            "wordpress",
            detect_format("post.json", '{"content":"<p>x</p>","slug":"x"}', "auto"),
        )
        self.assertEqual(
            "jsonld",
            detect_format("schema.json", '{"@type":"Article"}', "auto"),
        )

    def test_html_extracts_hreflang_and_citable_structures(self) -> None:
        html = """
        <link rel="alternate" hreflang="en" href="https://example.com/en">
        <ul><li>One</li></ul><table><tr><td>Two</td></tr></table><blockquote>Three</blockquote>
        """
        document = parse_document("page.html", html, "html")
        self.assertEqual(
            [{"lang": "en", "href": "https://example.com/en"}], document.hreflang
        )
        self.assertEqual(
            (1, 1, 1),
            (document.list_count, document.table_count, document.blockquote_count),
        )


if __name__ == "__main__":
    unittest.main()

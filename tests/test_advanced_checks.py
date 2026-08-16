from __future__ import annotations

import unittest

from content_seo_checker.geo import evaluate_geo
from content_seo_checker.hreflang import check_hreflang
from content_seo_checker.jsonld_diff import compare_jsonld, schema_nodes
from content_seo_checker.parsers import parse_document


class JsonLdDiffTests(unittest.TestCase):
    def test_removed_node_is_error(self) -> None:
        before = [
            {"@context": "https://schema.org", "@id": "#article", "@type": "Article"}
        ]
        findings = compare_jsonld(before, [], source="candidate.json")
        self.assertEqual("jsonld_diff.all_nodes_removed", findings[0].rule_id)

    def test_removed_property_is_warning(self) -> None:
        before = [
            {
                "@id": "#article",
                "@type": "Article",
                "headline": "Guide",
                "author": {"name": "A"},
            }
        ]
        after = [{"@id": "#article", "@type": "Article", "headline": "Guide"}]
        findings = compare_jsonld(before, after, source="candidate.json")
        self.assertIn(
            "jsonld_diff.property_removed", {item.rule_id for item in findings}
        )

    def test_changed_value_is_informational(self) -> None:
        before = [{"@id": "#article", "@type": "Article", "headline": "Old"}]
        after = [{"@id": "#article", "@type": "Article", "headline": "New"}]
        findings = compare_jsonld(before, after, source="candidate.json")
        self.assertEqual("jsonld_diff.value_changed", findings[0].rule_id)

    def test_graph_context_is_inherited(self) -> None:
        nodes = schema_nodes(
            [{"@context": "https://schema.org", "@graph": [{"@type": "Organization"}]}]
        )
        self.assertEqual("https://schema.org", nodes[0]["@context"])


class HreflangTests(unittest.TestCase):
    def _page(self, source: str, canonical: str, links: list[tuple[str, str]]):
        alternates = "".join(
            f'<link rel="alternate" hreflang="{language}" href="{href}">'
            for language, href in links
        )
        html = f'<html><head><link rel="canonical" href="{canonical}">{alternates}</head></html>'
        return parse_document(source, html, "html")

    def test_reciprocal_cluster_is_clean(self) -> None:
        links = [
            ("en", "https://example.com/en"),
            ("zh-CN", "https://example.com/zh"),
            ("x-default", "https://example.com/en"),
        ]
        en = self._page("en.html", "https://example.com/en", links)
        zh = self._page("zh.html", "https://example.com/zh", links)
        self.assertEqual([], check_hreflang([en, zh]))

    def test_missing_return_link_is_error(self) -> None:
        en = self._page(
            "en.html",
            "https://example.com/en",
            [("en", "https://example.com/en"), ("zh", "https://example.com/zh")],
        )
        zh = self._page(
            "zh.html", "https://example.com/zh", [("zh", "https://example.com/zh")]
        )
        rules = {item.rule_id for item in check_hreflang([en, zh])}
        self.assertIn("hreflang.return_link_missing", rules)

    def test_duplicate_and_invalid_language_are_errors(self) -> None:
        page = self._page(
            "page.html",
            "https://example.com/page",
            [
                ("english", "https://example.com/page"),
                ("english", "https://example.com/other"),
            ],
        )
        rules = {item.rule_id for item in check_hreflang([page])}
        self.assertIn("hreflang.language_invalid", rules)
        self.assertIn("hreflang.language_duplicate", rules)


class GeoContentTests(unittest.TestCase):
    def test_source_led_structured_article_is_clean(self) -> None:
        html = """
        <html><head><link rel="canonical" href="https://example.com/guide">
        <meta name="author" content="Editor">
        <script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","dateModified":"2026-08-16","author":{"name":"Editor"}}</script>
        </head><body><h1>Importer Guide</h1><h2>Summary</h2><p>Direct answer.</p>
        <h2>What evidence is required?</h2><ul><li>Certificate</li></ul>
        <h2>Decision process</h2><p>According to the <a href="https://www.wto.org/">WTO source</a>.</p>
        </body></html>
        """
        document = parse_document("guide.html", html, "html")
        self.assertEqual([], evaluate_geo(document))

    def test_weak_article_gets_stable_rules(self) -> None:
        document = parse_document(
            "weak.html", "<h1>Guide</h1><p>In 2026, adoption reached 75%.</p>", "html"
        )
        rules = {item.rule_id for item in evaluate_geo(document)}
        self.assertTrue(
            {
                "geo.summary_missing",
                "geo.citable_structure_missing",
                "geo.sources_missing",
                "geo.numeric_claim_unsourced",
                "geo.author_missing",
                "geo.freshness_missing",
            }.issubset(rules)
        )


if __name__ == "__main__":
    unittest.main()

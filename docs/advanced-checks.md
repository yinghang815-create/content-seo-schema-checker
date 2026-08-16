# Advanced pre-publish checks

## JSON-LD semantic diff

Compare the structured-data graph before and after a content change:

```bash
seo-schema-check jsonld-diff before.json after.json --fail-on warning
jsonld-diff-check before.json after.json --report sarif --output jsonld-diff.sarif
```

The comparison expands `@graph`, matches nodes by `@id` or type/label identity, and reports removed nodes, removed types, removed properties, additions, and changed values. Array values remain order-sensitive so ordered schema such as `BreadcrumbList` is not silently reordered.

## Hreflang and canonical clusters

```bash
seo-schema-check hreflang-canonical examples/hreflang
hreflang-canonical-check localized-pages/
```

The checker validates language codes, absolute and HTTPS URLs, duplicate languages, fragments, canonical self-references, and reciprocal links between locally supplied pages. It does not crawl URLs; include every page in a cluster when reciprocal validation is required.

## GEO content readiness

```bash
seo-schema-check geo-content article.html --fail-on warning
geo-content-lint content/ --report json --output geo-report.json
```

The deterministic GEO audit checks answer-first summaries, descriptive sectioning, citable lists/tables/quotes, external sources, sourced numeric claims, authorship, freshness metadata, and question-led sections. It does not estimate rankings or call an AI model.

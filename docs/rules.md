# Rule reference

Rule IDs are stable identifiers used in console, JSON, and SARIF reports.

| Rule ID | Default | Meaning |
| --- | --- | --- |
| `title.missing` | error | SEO title is absent |
| `title.too_short` | warning | Title is below the configured minimum |
| `title.too_long` | warning | Title exceeds the configured maximum |
| `description.missing` | error | Meta description is absent |
| `description.too_short` | warning | Description is below the minimum |
| `description.too_long` | warning | Description exceeds the maximum |
| `canonical.missing` | warning | Canonical URL is absent |
| `canonical.not_absolute` | error | Canonical URL is relative or malformed |
| `canonical.not_https` | warning | Canonical URL is not HTTPS |
| `robots.noindex` | error | Robots directives block indexing |
| `html.lang_missing` | warning | Document language is absent |
| `heading.h1_missing` | error | No H1 was found |
| `heading.multiple_h1` | error | More than one H1 was found |
| `heading.level_skipped` | warning | Heading hierarchy skips a level |
| `content.too_thin` | warning | Content is below the configured unit count |
| `image.alt_missing` | error | An image has no `alt` attribute |
| `link.href_missing` | warning | A link has an empty target |
| `social.og_title_missing` | warning | Open Graph title is absent |
| `social.og_description_missing` | warning | Open Graph description is absent |
| `social.og_image_missing` | warning | Open Graph image is absent |
| `social.twitter_card_missing` | warning | Twitter card metadata is absent |
| `schema.missing` | error | No JSON-LD was found |
| `schema.invalid_json` | error | A JSON-LD script is not valid JSON |
| `schema.context_missing` | error | A schema node lacks `@context` |
| `schema.context_invalid` | warning | `@context` does not reference schema.org |
| `schema.type_missing` | error | A schema node lacks `@type` |
| `schema.<type>.properties_missing` | error | Known schema type lacks expected properties |
| `schema.required_type_missing` | error | Configured schema type is absent |
| `wordpress.slug_missing` | error | WordPress payload has no slug |
| `wordpress.featured_media_missing` | warning | WordPress featured media is empty |
| `input.parse_failed` | error | Input could not be decoded or parsed |

Advanced command rule families are documented in
[advanced-checks.md](advanced-checks.md):

- `jsonld_diff.*` for structured-data regressions;
- `hreflang.*` for language/canonical clusters;
- `geo.*` for source, authorship, freshness, and citable content structure.

## Content units

Whitespace-separated Latin words and individual CJK characters both count as
content units. This avoids treating useful Chinese-language content as a single
word while keeping the threshold intuitive for English content.

## Schema property sets

The checker enforces pragmatic pre-publish property sets for common types:

- Article, BlogPosting, NewsArticle: `headline`, `image`, `author`,
  `datePublished`, `dateModified`, `mainEntityOfPage`;
- Product: `name`, `image`, `description`, `offers`;
- FAQPage: `mainEntity`;
- BreadcrumbList: `itemListElement`;
- Organization: `name`, `url`.

These checks are intentionally transparent and configurable. Search-engine
eligibility can change and may include policies that cannot be inferred from a
local source file.

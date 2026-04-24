# Structural Audit — Module 3

**Prompt**: Quel est le meilleur sérum anti-âge en 2026 selon les dermatologues ?
**Brand page**: https://lancome.fr/soin/par-categorie/serum-visage
**Cited pages analysed**: 3

## Verdict

Major structural gaps detected: 3 editorial, 4 schema. LLMs do not find the expected signal on the brand page — they fall back on the 3 editorial pages cited instead.

## Layer A — Editorial gaps (brand page vs majority of cited pages)

- H2 structure: the brand page has 0 H2s against an average of 4.3 on cited pages. LLMs favour structured pages (5+ H2s minimum).
- Ingredient coverage: 0 active ingredients named on the brand page against an average of 13.7 on cited pages. LLMs reason by active ingredient — a page that doesn't name them is invisible.
- Expert quotes: 100% of cited pages include quotes from dermatologists (MD, FAAD, DO). The brand page has none.

## Layer B — Structured-data gaps (schema.org)

- Schema `Product`: present on 3/3 cited pages, absent on the brand page.
- Schema `AggregateRating`: present on 3/3 cited pages, absent on the brand page.
- Schema `Review`: present on 2/3 cited pages, absent on the brand page.
- Schema `Article`: present on 3/3 cited pages, absent on the brand page.

## Prescriptive actions

1. Add at least 4 substantive H2 sections on the target page.
2. Explicitly name active ingredients in the copy: acide hyaluronique, ascorbate, azelaic, ceramide, collagen, collagene, collagène, céramide.
3. Include 1-2 dermatologist expert quotes (with MD/FAAD credibility explicitly visible) on the formulation of the key actives.
4. Implement JSON-LD `Product` on product and category pages.
5. Expose `AggregateRating` (rating value + review count) in JSON-LD.
6. Add `Review` JSON-LD for individual product reviews.
7. Restructure the page as `Article` with author, datePublished, and reviewedBy visible in JSON-LD.

## Per-page comparison

| URL | Citation rate | Type | H2 | Ingredients | Experts | Table | JSON-LD types |
|---|---|---|---|---|---|---|---|
| lancome.fr/soin/par-categorie/serum-visage | 0.00 | CATEGORY_PAGE | 0 | 0 | 0 | — | BreadcrumbList, ListItem, Organization, WebPage |
| vogue.fr/beaute/article/meilleurs-serums-anti-age | 0.36 | LISTICLE | 11 | 12 | 1 | — | AggregateRating, Article, BreadcrumbList, ListItem, Organization, Person, Product, Rating, Review |
| healthline.com/health/beauty-skin-care/best-anti-a | 1.00 | LISTICLE | 0 | 17 | 1 | ✓ | AggregateRating, Answer, Article, BreadcrumbList, FAQPage, ItemList, ListItem, Offer, Organization, Person, Product, Question |
| vogue.co.uk/article/best-anti-ageing-serums | 0.88 | LISTICLE | 2 | 12 | 2 | — | AggregateRating, Article, BreadcrumbList, ListItem, Organization, Person, Product, Rating, Review |
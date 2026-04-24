---
name: peec-structural-audit
description: "Module 3 of the Peec Brain plugin — THE DIFFERENTIATOR. Answers 'why doesn't ChatGPT cite my page when my competitors' pages are cited' across two structural layers no other submission in the Peec ecosystem aligns. Layer A — editorial structure: parses Peec get_url_content to measure H2/H3 density, named active ingredients, expert quotes (MD FAAD DO), comparison tables, standardised per-product sections, TOC / anchors, 'how we tested' and 'meet the experts' signals. Layer B — technical schema.org structure: parses raw HTML via extruct to count presence of JSON-LD types that cited pages ship (Product, AggregateRating, Review, FAQPage, HowTo, BreadcrumbList, Article, Organization) vs the brand page. Diff = signals present on a majority of cited pages but absent on the brand page. Output: markdown brief + JSON with verdict + editorial gaps + schema gaps + prescriptive actions. Trigger: 'why isn't my page cited by ChatGPT', 'structural audit of my page vs competitors', 'diff schema brand page vs cited pages', 'structural audit [prompt]', 'why do LLMs skip me on [prompt]', 'AI-ready content brief', 'structural comparison brand page vs LLM-cited pages'."
license: Stride Up — Peec Brain plugin
---

# peec-structural-audit

## When to use it

For each prompt where the brand has low Peec visibility and the Gap Analyzer (Module 2) has already identified a target page: the Structural Audit answers the question nobody else is answering — *why* is this specific page not being cited?

## Expected inputs

- `prompt_id` (str, required) — target Peec prompt ID
- `peec_project_id` (str, required)
- `brand_target_url` (str, required) — brand page to audit (typically output of Gap Analyzer)
- `n_cited_urls` (int, default 5) — number of LLM-cited pages to use as reference
- `run_layer_b` (bool, default true) — if false, skip the schema audit (for network-restricted environments)

## Outputs

- `structural_audit_<prompt_id>.md` — human-readable brief, shareable with content and dev teams
- `structural_audit_<prompt_id>.json` — downstream-exploitable structure
- JSON schema:
  - `prompt_text`, `brand_url`
  - `brand_audit` — editorial (h2_count, ingredient_mentions, expert_quote_count, ...) + schema (jsonld_types, has_product, has_aggregate_rating, ...)
  - `cited_audits` — same structure × N cited pages
  - `editorial_gaps` — list of human-readable strings
  - `schema_gaps` — list of strings
  - `prescriptive_actions` — list of strings
  - `verdict` — string

## Pipeline

1. Resolve `prompt_id` → `get_chat` + `list_chats` to extract the URLs actually cited (Peec `get_url_report` filtered by prompt_id is the recommended path).
2. `get_url_content` on each cited URL + the brand URL → markdown content extracted by Peec.
3. **Layer A (editorial)**: parse markdown with regex for each signal. No network dependency.
4. **Layer B (schema)**: fetch raw HTML for each URL (via requests, or via `scripts/fetch_and_audit.py` standalone if sandbox). Parse with `extruct` → extract JSON-LD / microdata / RDFa / Open Graph.
5. Aggregate: mean / ratio per signal across cited pages.
6. Diff: emit a gap when a signal is present on ≥ 50% of cited pages but absent on the brand page.
7. Generate prescriptive actions + verdict.

## MCP tools used

- Peec AI MCP: `list_chats`, `get_chat`, `get_url_content`, `get_url_report`
- Python dependencies: `extruct`, `requests`, `w3lib`

## Implementation notes

- Peec `get_url_content` returns markdown processed via Mozilla Readability, which strips `<script type="application/ld+json">` tags. Layer B therefore needs to fetch raw HTML separately.
- A standalone script `scripts/fetch_and_audit.py` is provided for restricted environments (Cowork sandbox): it fetches + extracts offline, produces a JSON consumable by this skill in `--schema-from` mode.
- Anti-false-positive filters on expert-quote patterns: excludes brand names like "Dr Jart" but keeps real experts like "Dr Jenny Liu, MD FAAD".
- Peec's URL classification (`HOMEPAGE`, `CATEGORY_PAGE`, `PRODUCT_PAGE`, `LISTICLE`, `COMPARISON`, etc.) is preserved in the output and used to adjust the verdict — a content-less CATEGORY_PAGE has a different diagnostic than a poorly structured LISTICLE.

## Real-world validation

Run on Lancôme × prompt "best anti-aging serum 2026 according to dermatologists" (0% visibility) → diagnostic generated: 3 editorial gaps + 4 schema gaps + 7 prescriptive actions. Verdict: the Lancôme category page has no H2s, no named active ingredient, no cited expert, no Product/AggregateRating/Review/Article JSON-LD, while 3/3 cited pages (Vogue FR, Healthline, Vogue UK) all ship Article + multiple Product-family types.

## Status

Version 1.0 — operational on real data. Next upgrades: automatic raw-HTML fetch (currently via standalone script), multi-prompt batch support, one-call composite "content brief" generation.

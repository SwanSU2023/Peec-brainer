---
name: peec-gap-analyzer
description: "Module 2 of the Peec Brain plugin. Produces the prioritized list of client pages to optimise for AI visibility using a traffic-first approach that differentiates from the other content-gap analyzers in the challenge (Ritwika workflow-1, Lukas content-gap-hunt, Drift Radar). Formula: priority_score = Ahrefs_top_page_traffic × (1 − AI_visibility_Peec). The signal: a page already earning 1 000+ monthly visits on Google but invisible in LLMs is where every euro of optimisation work should land first. Filters branded prompts by default (visibility on those is structurally high). Enriches each row with page_type (commercial / editorial / landing / other) and top-3 competitors occupying the gap. Cross-references Peec get_brand_report (per-prompt visibility) with Ahrefs site-explorer-top-pages (real per-URL traffic). Output is a CSV the content team can execute directly. Trigger: 'analyse my Peec gaps', 'which pages to optimise for LLMs', 'content gap analysis prioritised by traffic', 'content gap [brand]', 'pages invisible in ChatGPT', 'traffic-first content gap'."
license: Stride Up — Peec Brain plugin
---

# peec-gap-analyzer

## When to use it

Weekly, on each client account, to produce the content team's optimisation backlog for the week.

## Expected inputs

- `domain` (str, required) — client domain
- `peec_project_id` (str, required) — target Peec project
- `country` (str, default "fr")
- `include_branded` (bool, default false) — if false, skip prompts tagged `branded:branded`
- `min_traffic` (int, default 100) — minimum monthly traffic on the client page to be retained

## Outputs

CSV `content_gaps.csv` with columns:
- `rank`
- `url`
- `page_type` (commercial / editorial / landing / other)
- `traffic_month`
- `visibility_pct`
- `prompt_id`, `prompt_text`
- `branded` (branded | non_branded)
- `top3_competitors_occupying` (pipe-separated list)
- `priority_score`
- `suggested_action`

## Pipeline

1. `get_brand_report` with `prompt_id` dimension → per-prompt visibility for the own brand.
2. Filter prompts by `branded:non_branded` tag (default) unless `include_branded=true`.
3. `site-explorer-top-pages` on the client domain → per-URL traffic.
4. Match URL × prompt via keyword-token Jaccard overlap.
5. For each matched pair, compute `priority_score = traffic × (1 − visibility)`.
6. For each prompt in the gap list, aggregate `brands_mentioned[]` from recent chats to produce the `top3_competitors_occupying` column.
7. Classify `page_type` via URL regex (commercial / editorial / landing / other).
8. Rank and export CSV.

## MCP tools used

- Peec AI MCP: `get_brand_report`, `list_brands`, `list_prompts`, `list_chats`, `get_chat`
- Ahrefs MCP: `site-explorer-top-pages`

## Implementation notes

- Rank 1 is always the highest `priority_score`. Ties are broken by higher traffic.
- URL classification is a simple regex, not an LLM call — fast and auditable.
- The top-3 competitors per prompt are aggregated over the last 30 days (configurable).

## Status

Version 1.1 — validated on Lancôme → 20 pages prioritised, top gap = `/beauty-magazine/la-routine-skincare-parfaite-pour-ma-peau.html` (1 169 visits/mo, 0% visibility on 5 prompts, competitors La Roche-Posay / Clarins / Sisley).

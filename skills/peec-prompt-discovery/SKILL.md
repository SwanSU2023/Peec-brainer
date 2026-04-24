---
name: peec-prompt-discovery
description: "Module 1 of the Peec Brain plugin. Generates Peec AI prompts to track by fusing THREE SEO sources for results that no single source produces on its own: (1) GSC queries when ownership is available, (2) Ahrefs site-explorer-organic-keywords for rank and traffic data, (3) a client product catalog to reach specific product-name prompts (e.g. 'La Vie Est Belle Intense reviews') that GSC-only or keyword-only tools cannot reach. Also ships a branded/non-branded overlay: non-branded prompts are pushed to Peec by default, branded ones go to a backlog CSV. Classifies intent (informational / commercial / branded / comparison / transactional), reformulates into natural questions, deduplicates against existing Peec prompts, proposes topics, creates in batch via create_prompts. Dry-run by default. Trigger: 'generate my Peec prompts', 'multi-source prompt discovery', 'fuse GSC + Ahrefs + catalog into Peec', 'bootstrap Peec for [brand]', 'discover prompts to track on [domain]'."
license: Stride Up — Peec Brain plugin
---

# peec-prompt-discovery

## When to use it

Whenever a new client joins the Peec portfolio and needs initial prompt seeding — or periodically (monthly) to enrich existing prompts as the domain's keywords evolve.

## Expected inputs

- `domain` (str, required) — client domain (e.g. "lancome.com")
- `peec_project_id` (str, required) — target Peec project
- `min_volume` (int, default 100) — minimum search volume for an Ahrefs keyword to be retained
- `max_prompts` (int, default 30) — max prompts created per pass
- `dry_run` (bool, default true) — if true, list candidates without creating them in Peec

## Outputs

- If `dry_run=true`: `prompt_candidates.csv` with columns `[query, volume, intent, branded, topic_suggested, status]`
- If `dry_run=false`: prompts created in Peec, IDs returned, + audit CSV
- When the branded/non-branded overlay is active: split output into `prompts_non_branded.csv` (priority push) + `prompts_branded_backlog.csv` (opt-in push).

## Pipeline

1. List existing Peec prompts (`list_prompts`) for the target project.
2. Fetch the top Ahrefs organic keywords for the domain (`site-explorer-organic-keywords`).
3. Filter by minimum volume and deduplicate.
4. Reformulate each keyword into a natural question (template or LLM).
5. Classify intent: informational / commercial / branded / comparison / transactional.
6. Classify branded vs non-branded using the client's `brand_patterns`, `product_patterns`, `subbrand_patterns`.
7. Match against existing Peec topics or propose new ones.
8. Dedupe against existing Peec prompts (string similarity + embeddings).
9. Batch create: `create_topics` then `create_prompts` in groups of 5. Tag each with `branded:non_branded` or `branded:branded`.

## MCP tools used

- Peec AI MCP: `list_projects`, `list_topics`, `list_prompts`, `list_tags`, `create_topics`, `create_prompts`, `create_tags`
- Ahrefs MCP: `site-explorer-organic-keywords`, `keywords-explorer-matching-terms`

## Implementation notes

- Rate limits: max 5 prompts per call, 1s sleep between batches.
- Query-to-question reformulation can use a simple template: "What is [X]?", "How [Y]?", "Best [Z]" depending on intent.
- For multilingual brands, filter keywords by `country_code` (defaults to FR).
- The branded/non-branded classification is accent-insensitive and case-insensitive.

## Status

Version 1.0 — validated on Lancôme → 22 prompts proposed across 6 topics (split 16 branded / 6 non-branded) from 57 existing prompts + 30 GSC/Ahrefs keywords. Next extensions: product-name detection via embeddings for more resilient matching, multi-language pipeline.

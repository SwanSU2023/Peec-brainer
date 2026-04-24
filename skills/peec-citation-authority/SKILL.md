---
name: peec-citation-authority
description: "Module 4 of the Peec Brain plugin. Answers 'who cites my competitors and never me, and how do I reach them' — no other submission in the Peec ecosystem productises this audit (Eoghan mentions it as a recipe in peec-ai-mcp §11, we are the first to ship it as a workflow). Outputs an outreach-ready prioritized list of the source domains citing at least one tracked competitor but never the own brand. Pipeline: Peec get_domain_report filtered by prompt_id → cited domains + mentioned_brand_ids + Peec classification (EDITORIAL / UGC / CORPORATE / …); build gap list = domains citing competitors but not the brand; Ahrefs site-explorer-domain-rating enrichment → DR + ahrefs_rank per domain; typology classification via curated whitelist (editorial_premium Vogue/Forbes/Elle, editorial_health Healthline/Top Santé, specialized Byrdie/Paula's Choice, retailer Sephora/Douglas, UGC Reddit/Beautylish, reference PubMed/Wikipedia, corporate); priority score = (citation_count + retrieval_count × 0.3) × (DR/100) × typology_weight; recommended outreach action per typology. CSV output is directly actionable by the PR/Digital PR team. Trigger: 'who cites my competitors and not me', 'citation authority audit', 'AI-aware Digital PR outreach list', 'sources driving my competitors' visibility', 'PR plan [brand]', 'citation gap analysis'."
license: Stride Up — Peec Brain plugin
---

# peec-citation-authority

## When to use it

Quarterly per brand, or after Module 2 for the prioritized prompts: the Citation Authority Audit is the deliverable between the SEO/AI team and the PR/communications team. It transforms Peec + Ahrefs data into an actionable outreach roadmap.

The pitch: *"Here are the 25 domains that decided not to talk about you, and here is who they cite in your place. Your next-quarter PR campaign starts here."*

## Expected inputs

- `peec_project_id` (str, required)
- `prompt_ids` (list[str], required) — one or more prompts to analyse (typically the low-visibility ones)
- `own_brand_id` (str, required) — the `is_own=true` brand_id of the brand
- `competitor_brand_ids` (list[str], optional) — restrict the analysis to domains citing these competitors. If empty, uses every tracked brand in the project.
- `min_citations` (int, default 2) — minimum citation_count for a domain to be included
- `enrich_dr` (bool, default true) — if false, skip the Ahrefs DR enrichment

## Outputs

- `citation_authority_<prompt_label>.csv` — columns: `domain, typology, outreach_priority, priority_score, domain_rating, ahrefs_rank, citation_count, retrieval_count, citation_rate, competitor_count, cited_competitors, peec_classification, recommended_action, notes`
- Sorted by `priority_score` desc
- Three buckets: HIGH / MEDIUM / LOW

## Pipeline

1. Peec `get_domain_report` filtered by `prompt_ids`, ordered by `citation_count`, limit 100. Ensure `mentioned_brand_ids[]` is in the output.
2. Build the gap list: for each returned domain, check that `own_brand_id not in mentioned_brand_ids` AND at least one `competitor_brand_id` appears.
3. For each retained domain, call Ahrefs `site-explorer-domain-rating` → DR + ahrefs_rank. Cache (DR evolves slowly).
4. Classify in a typology via curated domain whitelist, then fall back to the Peec classification when the domain is not in the whitelist.
5. Score: `(citation_count + retrieval_count × 0.3) × (DR / 100) × typology_weight`. Weights: editorial_premium 1.00, editorial_health 0.90, specialized 0.85, retailer 0.60, reference 0.40, ugc 0.30, corporate 0.20, institutional 0.20, competitor 0.10.
6. Bucket: HIGH ≥ 5.0, MEDIUM ≥ 1.5, else LOW.
7. Resolve each cited `brand_id` to its name via `list_brands`.
8. Emit the recommended action by typology.
9. Export the CSV.

## MCP tools used

- Peec AI MCP: `get_domain_report` (with prompt_id filter + dimensions), `list_brands`
- Ahrefs MCP: `site-explorer-domain-rating` (one call per domain)
- Optional for finer typology: classification via a short Claude prompt

## Implementation notes

- `mentioned_brand_ids` is returned by Peec in each row of `get_domain_report` — this is what makes the gap analysis possible without traversing every chat individually.
- Ahrefs enrichment: batch DR calls in waves of 5 to avoid stream timeouts. Expected cost ≈ 2 units per call.
- The typology whitelist lives in `peec_brain/citation_authority.py` (`_EDITORIAL_PREMIUM`, `_EDITORIAL_HEALTH`, `_SPECIALIZED_BEAUTY`, `_RETAILERS`, `_UGC`, `_REFERENCE`). Extend per client sector.
- Keep `peec_classification` in the output: it serves as a double-check when the whitelist misses a domain.

## Real-world validation

Run on Lancôme × prompt "best anti-aging serum 2026 according to dermatologists" → 15 cited domains over 30 days, 11 GAP (citing competitors, never Lancôme), 5 HIGH priority: vogue.co.uk (DR 87), today.com (DR 90), forbes.com (DR 94), nymag.com (DR 90), healthline.com (DR 92). The top target (vogue.co.uk) cites Allies of Skin, Chanel, Dr Dennis Gross, Elemis, SkinCeuticals. CSV delivered directly to the PR team.

## Status

Version 1.0 — operational on real Lancôme data. Next upgrades: multi-prompt batch (aggregate on a pool of prompts instead of a single one), Ahrefs referring-domains enrichment to detect whether prior outreach already succeeded, month-over-month tracking (does the same domain appear more often over time?).

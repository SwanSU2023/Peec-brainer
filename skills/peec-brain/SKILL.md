---
name: peec-brain
description: "Orchestrator for the Peec Brain plugin. Designed for SEO agencies and in-house brand teams piloting AI search visibility. Chains the four sub-skills across a 2x2 matrix (page × source / what × why): peec-prompt-discovery to generate the prompts to track (fusion of GSC + Ahrefs + product catalog), peec-gap-analyzer to prioritise pages to optimise (traffic-first), peec-structural-audit to diagnose why pages are not cited (editorial + schema.org), peec-citation-authority to list the domains citing competitors but never the brand (outreach-ready CSV). Runs in onboarding mode (new client — full pipeline), weekly (review minus discovery), or adhoc (single prompt audit). Trigger: 'run Peec Brain', 'onboarding AI visibility for [client]', 'full Peec Brain pipeline', 'Peec Brain weekly on [brand]', 'complete AI visibility audit on [prompt]'."
license: Stride Up — Peec Brain plugin
---

# peec-brain

## When to use it

Single entry point for the plugin. Three modes:

- **Onboarding mode** — a new client joins the portfolio → full pipeline 1 → 2 → 3 → 4.
- **Weekly mode** — recurring review on an active account → skip Module 1 (prompts already created), run Modules 2 → 3 → 4.
- **Adhoc mode** — one-off audit on a specific prompt → run Modules 3 + 4 only.

## Expected inputs

- `domain` (str, required)
- `peec_project_id` (str, required)
- `own_brand_id` (str, required) — the `is_own=true` brand_id of the client
- `client_name` (str, required)
- `mode` (str, default `"weekly"`) — `"onboarding"` | `"weekly"` | `"adhoc"`
- `target_prompts` (list[str], optional) — prompts to focus on in adhoc mode. In weekly mode the default is all prompts with visibility < 30%.
- `schedule_weekly` (bool, default false) — if true, schedule via `anthropic-skills:schedule`.

## Outputs per mode

| Mode | M1 | M2 | M3 | M4 | Artifact |
|---|---|---|---|---|---|
| onboarding | ✓ create | ✓ | ✓ top 3 prompts | ✓ | ✓ create |
| weekly | — | ✓ | ✓ top 3 new gaps | ✓ delta | ✓ update |
| adhoc | — | — | ✓ single prompt | ✓ single prompt | — |

Files produced:
- `prompts_created.csv` (onboarding) — Module 1 output
- `content_gaps.csv` — Module 2 output
- `structural_audit_<prompt>.md` + `.json` — Module 3 output per prompt
- `citation_authority_<prompt>.csv` — Module 4 output per prompt
- URL of the refreshable Cowork artifact

## Detailed pipeline

### Onboarding mode (new client)

1. `peec-prompt-discovery` with `dry_run=false` → creates 20-30 prompts + 5-6 topics.
2. Wait 24h for Peec collection (or skip for live demo).
3. `peec-gap-analyzer` → CSV of the top 20 priority pages.
4. For the 3 highest-priority prompts (0% visibility + high traffic):
   - `peec-structural-audit` → per-prompt brief
   - `peec-citation-authority` → per-prompt PR CSV
5. `peec-radar-artifact` in create mode → URL for the client deliverable.

### Weekly mode

1. `peec-gap-analyzer` → detects new gaps.
2. For the 3 prompts where visibility dropped:
   - `peec-structural-audit`
   - `peec-citation-authority`
3. `peec-radar-artifact` update.
4. If `schedule_weekly=true`, schedule the next iteration.

### Adhoc mode (single-prompt audit)

1. `peec-structural-audit` on the target prompt.
2. `peec-citation-authority` on the same prompt.
3. Returns the brief + outreach CSV in a single pass.

## Dependent skills

- `peec-prompt-discovery` (Module 1)
- `peec-gap-analyzer` (Module 2)
- `peec-structural-audit` (Module 3)
- `peec-citation-authority` (Module 4)
- `peec-radar-artifact` (optional — client-facing output)
- `anthropic-skills:schedule` (optional — weekly automation)

## Implementation notes

- Each sub-skill is callable independently; this skill chains them but doesn't duplicate their logic.
- Priority execution order when budget is constrained: M3 > M4 > M2 > M1 (most differentiating first).
- Error handling: if M3 fails on a prompt (e.g. no chats available), move to the next without blocking M4.
- Log each transition explicitly between modules.
- E-E-A-T tip: emit an executive summary at the end of the run recapping "3 major gaps + 5 HIGH-priority outreach domains".

## Status

Version 1.0 — 4 modules running on real Lancôme data. Conceptual orchestrator; Cowork chains the skills on demand. Version 2.0 planned with direct Python CLI orchestration (`peec-brain run --mode weekly --project ...`).

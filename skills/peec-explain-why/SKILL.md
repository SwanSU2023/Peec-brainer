---
name: peec-explain-why
description: "Legacy module — superseded by peec-structural-audit (Module 3) which carries over its editorial Layer A and adds the schema.org Layer B. Kept in the codebase for backward compatibility. For a Peec prompt where the brand has low AI visibility, it explains why the LLMs don't cite the brand page and emits an AI-ready content brief. Trigger: 'explain why', 'why doesn't ChatGPT cite [brand] on [prompt]', 'AI content brief', 'brief for this prompt', 'per-prompt gap analysis', 'how to be cited by LLMs on [prompt]', 'diagnose this Peec prompt'."
license: Stride Up — Peec Brain plugin
---

# peec-explain-why (legacy)

> This skill has been folded into `peec-structural-audit` (Module 3) which extends the original editorial analysis with a schema.org audit layer. Use `peec-structural-audit` for all new runs. The files here are kept in place for backward compatibility only.

## Expected inputs

- `prompt_id` (str, required) — Peec prompt ID
- `peec_project_id` (str, required)
- `target_url` (str, required) — client URL supposedly targeting this prompt (typically from Gap Analyzer)
- `n_chat_samples` (int, default 5) — number of LLM responses sampled to derive expected topics
- `models` (list, optional) — restrict analysis to specific engines (e.g. ["chatgpt-scraper", "perplexity-scraper"])

## Outputs

- Markdown brief — readable by the content team
- JSON structure for downstream consumption

## Pipeline (legacy — editorial only)

1. `list_chats` on the prompt_id + recent-date filter
2. `get_chat` on N samples to extract the assistant response text
3. Parse responses for H2/H3 topics (ingredients, sub-themes, product categories)
4. Aggregate recurring topics → "expected topics" list
5. Extract mentioned brands from each chat → "citation competitors" list
6. `get_url_content` on target_url → markdown
7. Compute coverage: expected-topics tokens ∩ page-content tokens
8. Generate the brief

## Status

Superseded by `peec-structural-audit`. Do not use for new work.

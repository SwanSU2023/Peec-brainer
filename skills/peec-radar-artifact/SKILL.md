---
name: peec-radar-artifact
description: "Creates or updates a refreshable Cowork 'Peec Brain Radar' artifact that consolidates the three Gap Analyzer outputs (content gaps, digital PR targets, competitor wins) into a single client-facing dashboard. The artifact calls the Peec and Ahrefs MCPs on every open, so the data stays fresh. Usable as a white-label agency deliverable. Trigger: 'create my Peec radar', 'Peec Brain dashboard', 'AI visibility artifact', 'client deliverable Peec', 'weekly Peec radar', 'update my Peec radar'."
license: Stride Up — Peec Brain plugin
---

# peec-radar-artifact

## When to use it

After a Gap Analyzer run, to materialise the three outputs into a refreshable Cowork artifact. The artifact becomes the weekly deliverable consumed by SEO teams or shared with the client.

## Expected inputs

- `domain` (str, required) — client domain
- `peec_project_id` (str, required)
- `client_name` (str, required) — shown in the artifact header
- `gap_analyzer_output` (path or dict) — result from `peec-gap-analyzer`
- `branding` (dict, optional) — `{logo_url, primary_color, secondary_color}`

## Outputs

- URL of the created Cowork artifact (persistent, shareable)
- Update mode: refreshes the existing artifact without recreating it

## Artifact structure

Three tabs:
- **Content Gaps** — filterable table of pages to optimise, priority_score gradient
- **Digital PR** — table of domains to pitch + domain cards with DR / citation counts
- **Competitor Wins** — timeline of competitor pages gaining citations + action suggestions

Header: client name, last-refresh timestamp, `Refresh from Peec` button.
Footer: `#BuiltWithPeec` + discreet Stride Up logo.

## Refresh mechanism

The artifact calls `window.cowork.callMcpTool()` to re-run the Peec and Ahrefs MCPs on demand. Example:

```js
const chats = await window.cowork.callMcpTool('peec:list_chats', { project_id, limit: 100 });
// then local orchestration to recompute the three outputs
```

## MCP tools used

- Cowork: `create_artifact`, `update_artifact`
- At runtime inside the artifact: `list_chats`, `list_prompts`, `get_domain_report`, `site-explorer-*`, `brand-radar-*`

## Design notes

- Palette: navy #1F2A44 / blue #2E75B6 / light #D5E8F0 / grey #F2F2F2
- Typography: system-ui (no web fonts)
- Responsive: single column below 768px
- No CSS framework (keeps dependencies minimal)

## Status

Version 0.1 — skeleton. HTML template lives at `dashboard/index.html` and is built via `scripts/build_dashboard.py`.

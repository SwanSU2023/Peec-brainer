---
name: peec-explain-why
description: "Pour un prompt Peec où la marque a une faible visibility AI, explique pourquoi les LLMs ne citent pas le client sur cette requête et génère un brief de contenu AI-ready. Analyse la structure des réponses LLM (via get_chat) pour extraire les topics attendus, récupère le contenu de la page cible (via get_url_content), et calcule la couverture. Output : un brief markdown avec diagnostic, topics manquants, H2 recommandés, action items. C'est la seule feature du plugin qui répond à la question 'pourquoi ChatGPT ne me cite pas ?'. Trigger : 'explain why', 'pourquoi ChatGPT ne cite pas [marque] sur [prompt]', 'content brief AI', 'brief pour ce prompt', 'gap analysis par prompt', 'comment être cité par les LLMs sur [prompt]', 'diagnose this Peec prompt'."
license: Stride Up — Peec Brain plugin
---

# peec-explain-why

## Quand l'utiliser

Après le Gap Analyzer, pour chaque prompt priorisé avec faible visibility : tu veux un brief actionnable pour l'équipe contenu. Ce skill transforme un gap identifié en plan d'action précis.

## Inputs attendus

- `prompt_id` (str, requis) : l'ID du prompt Peec à analyser
- `peec_project_id` (str, requis)
- `target_url` (str, requis) : l'URL client supposée cible pour ce prompt (typiquement issue du Gap Analyzer)
- `n_chat_samples` (int, default 5) : nombre de réponses LLM à analyser pour dériver les topics attendus
- `models` (list, optional) : restreindre l'analyse à certains moteurs (ex. ["chatgpt-scraper", "perplexity-scraper"])

## Outputs

- Markdown brief (`content_brief_<prompt_id>.md`) — humainement lisible, partageable en tant que livrable rédacteur
- JSON structuré (`content_brief_<prompt_id>.json`) — consommable par l'artifact ou un workflow aval
- Schéma JSON :
  - `prompt_text` (str)
  - `page_url`, `page_classification` (str)
  - `current_visibility_pct` (str)
  - `expected_topics_count` / `covered_topics_count` (int)
  - `coverage_ratio` (float)
  - `missing_topics` (list[str])
  - `citation_competitors` (list[str]) — marques citées par les LLMs sur ce prompt
  - `recommended_h2s` (list[str])
  - `diagnosis` (str)
  - `action_items` (list[str])

## Pipeline

1. `list_chats` sur le prompt_id + filtre date récente
2. `get_chat` sur N échantillons pour récupérer le texte des réponses assistant
3. Parse les réponses pour extraire les topics H2/H3 (ingrédients, sous-thèmes, catégories de produits)
4. Agrège les topics fréquents → liste "expected topics"
5. Extrait les marques citées depuis `brands_mentioned` sur chaque chat → liste "citation competitors"
6. `get_url_content` sur target_url → contenu markdown de la page client
7. Calcule la couverture : tokens des topics attendus ∩ tokens du contenu page
8. Génère le brief (diagnostic + H2 recommandés + action items)

## MCP tools mobilisés

- Peec AI MCP : `list_chats`, `get_chat`, `get_url_content`
- Optionnel : `get_brand_report` (pour confirmer visibility sur le prompt avant analyse)

## Notes d'implémentation

- Le parsing des topics utilise : regex sur les markdown headings (`##`, `###`), bold emphasis (`**X**`), avec filtres anti-meta (exclut "tendances", "exemples populaires", "conclusion")
- Strip des numérotations (`### 1. **X**` → `X`) et parenthèses clarificatives (`Retinol (ou Retinoïdes)` → `Retinol`)
- Filtre les headings qui sont des noms de marques (pas des topics)
- Coverage = (topics dont ≥60% des tokens sont dans le contenu page) / total expected topics
- Diagnostic prend en compte : classification URL (CATEGORY_PAGE vs EXPLAINER), nombre de H2, paragraph count, coverage ratio

## Statut

Version 0.2 — fonctionnel sur Lancôme (prompt "meilleur sérum anti-âge dermatologues" → 0/6 coverage identifiée, brief généré). Extension prévue en v0.3 : fetch du contenu de 1-2 pages concurrentes citées pour une comparaison structurelle directe.

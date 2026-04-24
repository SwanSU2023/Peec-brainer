---
name: peec-gap-analyzer
description: "Module 2 du plugin Peec Brain. Produit la liste priorisée des pages client à optimiser pour l'AI visibility, via une priorisation TRAFIC-FIRST — différenciant par rapport aux autres content-gap analyzers du challenge (Ritwika workflow-1, Lukas content-gap-hunt, Drift Radar). La formule : priority_score = trafic_Ahrefs_top_page × (1 − AI_visibility_Peec). Le signal : une page qui fait déjà 1 000+ visites mensuelles depuis Google mais invisible dans les LLMs, c'est là que chaque euro d'optimisation doit aller en premier. Croise Peec get_brand_report (visibility par prompt) avec Ahrefs site-explorer-top-pages (trafic réel par URL). Output CSV exploitable direct par l'équipe contenu. Trigger : 'analyse mes gaps Peec', 'quelles pages optimiser pour les LLMs', 'content gap analysis prioritized by traffic', 'content gap [marque]', 'pages invisibles dans ChatGPT', 'traffic-first content gap'."
license: Stride Up — Peec Brain plugin
---

# peec-gap-analyzer

## Quand l'utiliser

En revue hebdomadaire d'un compte client pour prioriser les actions SEO "AI-first" : quelles pages optimiser, quels sites contacter, quelles pages concurrentes surveiller.

## Inputs attendus

- `domain` (str, requis) : domaine du client
- `peec_project_id` (str, requis) : ID projet Peec
- `competitor_domains` (list, optional) : domaines concurrents à surveiller
- `min_traffic_page` (int, default 500) : trafic minimum par page pour être retenu
- `min_citations_domain` (int, default 3) : fréquence minimum de citation pour un domaine Digital PR

## Outputs

Trois CSV (+ optionnel : consolidation JSON pour artifact) :

1. `content_gaps.csv` — colonnes : `page_url`, `query`, `impressions`, `ai_visibility_score`, `priority_score`
2. `digital_pr.csv` — colonnes : `domain`, `citations_count`, `domain_rating`, `has_backlink`, `suggested_action`
3. `competitor_wins.csv` — colonnes : `competitor_url`, `topic`, `citations_gained_30d`, `replica_suggestion`

## Pipeline

### Output 1 — Content Gaps

1. Pour chaque prompt du projet Peec, échantillonner N chats et mesurer `ai_visibility_score = mentions_brand / total_chats`
2. Pour chaque prompt avec score bas (< 30%), trouver les pages du client qui rankent sur ce prompt côté organic (via `site-explorer-organic-keywords` filtré par URL)
3. Calculer `priority_score = impressions_page × (100 - ai_visibility_score)`
4. Trier par priority_score décroissant

### Output 2 — Digital PR Hit List

1. Agréger les domaines cités dans tous les chats Peec via `get_domain_report` (ou parsing des chats)
2. Filtrer par `citations_count >= min_citations_domain`
3. Cross-ref avec `site-explorer-referring-domains` du client
4. Si domaine cité par LLMs MAIS absent des referring domains → cible Digital PR
5. Enrichir : Domain Rating, nombre estimé de contacts, types de contenus

### Output 3 — Competitor Wins

1. Pour chaque concurrent, appeler `brand-radar-cited-pages` sur la période récente
2. Identifier les pages qui ont gagné en citations sur les 30 derniers jours
3. Matcher contre le sitemap client pour détecter les gaps de contenu
4. Suggérer action : créer page équivalente, optimiser page existante, ou outreach

## MCP tools mobilisés

- Peec AI MCP : `list_prompts`, `list_chats`, `get_chat`, `get_brand_report`, `get_domain_report`, `get_url_report`
- Ahrefs MCP : `site-explorer-organic-keywords`, `site-explorer-top-pages`, `site-explorer-referring-domains`, `brand-radar-cited-domains`, `brand-radar-cited-pages`

## Notes d'implémentation

- Échantillonnage des chats : 50-100 par prompt suffit pour un score stable
- Cross-ref referring domains : matcher sur le domaine racine, pas l'URL complète
- Pour les concurrents, reutiliser la liste `is_own = false` de `list_brands`

## Statut

Version 0.1 — squelette. À compléter une fois client vitrine confirmé.

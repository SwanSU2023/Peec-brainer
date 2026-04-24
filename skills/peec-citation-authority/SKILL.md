---
name: peec-citation-authority
description: "Module 4 du plugin Peec Brain. Répond à la question 'qui cite mes concurrents et jamais moi, et comment les atteindre' — aucun autre outil de l'écosystème Peec Challenge ne productise cet audit (Eoghan le mentionne comme recette dans peec-ai-mcp §11, on est les premiers à le shipper en workflow). Sort une liste priorisée outreach-ready des domaines source qui citent au moins un concurrent tracké mais jamais la marque. Pipeline : Peec get_domain_report filtré par prompt_id → domaines cités + mentioned_brand_ids + Peec classification (EDITORIAL / UGC / CORPORATE / …) ; build gap list = domaines citant des concurrents mais pas la marque ; enrichissement Ahrefs site-explorer-domain-rating → DR + ahrefs_rank par domaine ; classification typologique via whitelist curée (editorial_premium Vogue/Forbes/Elle, editorial_health Healthline/Top Santé, specialized Byrdie/Paula's Choice, retailer Sephora/Douglas, UGC Reddit/Beautylish, reference PubMed/Wikipedia, corporate) ; priority score = (citation_count + retrieval_count × 0.3) × (DR/100) × typology_weight ; action outreach recommandée par typologie. Output CSV exploitable direct par équipe RP/Digital PR. Trigger : 'qui cite mes concurrents et pas moi', 'audit citation authority', 'liste outreach Digital PR AI-aware', 'sources qui font la visibilité de mes concurrents', 'plan RP [marque]', 'citation gap analysis'."
license: Stride Up — Peec Brain plugin
---

# peec-citation-authority

## Quand l'utiliser

Trimestriellement par marque, ou post-Module 2 pour les prompts priorisés : le Citation Authority Audit est le livrable entre équipe SEO/AI et équipe RP/communication. Il transforme les données Peec + Ahrefs en une feuille de route outreach actionnable.

Le pitch : *"Voici les 25 domaines qui ont décidé de ne pas parler de vous, et voici qui ils citent à votre place. Votre campagne RP du trimestre prochain commence ici."*

## Inputs attendus

- `peec_project_id` (str, requis)
- `prompt_ids` (list[str], requis) : un ou plusieurs prompts à analyser (typiquement ceux en faible visibility)
- `own_brand_id` (str, requis) : le `is_own=true` brand_id de la marque
- `competitor_brand_ids` (list[str], optional) : restreint l'analyse aux domaines citant ces concurrents. Si vide, utilise toutes les brands trackées du projet.
- `min_citations` (int, default 2) : seuil minimum de citation_count pour inclure un domaine
- `enrich_dr` (bool, default true) : si false, skip l'enrichissement Ahrefs DR

## Outputs

- `citation_authority_<prompt_label>.csv` — colonnes : `domain, typology, outreach_priority, priority_score, domain_rating, ahrefs_rank, citation_count, retrieval_count, citation_rate, competitor_count, cited_competitors, peec_classification, recommended_action, notes`
- Trié par priority_score décroissant
- Trois buckets : HIGH / MEDIUM / LOW

## Pipeline

1. Peec `get_domain_report` filtré par `prompt_ids`, `order_by=citation_count`, `limit=100`. Inclure `mentioned_brand_ids[]` dans l'output.
2. Build la gap list : pour chaque domaine retourné, vérifier que `own_brand_id not in mentioned_brand_ids` ET qu'au moins un `competitor_brand_id` apparaît.
3. Pour chaque domaine retenu, appel Ahrefs `site-explorer-domain-rating` → DR + ahrefs_rank. Mettre en cache (DR ne change pas vite).
4. Classifier en typologie via whitelist curée par domaine, puis fallback sur la classification Peec si domaine inconnu.
5. Score : `(citation_count + retrieval_count × 0.3) × (DR / 100) × typology_weight`. Weights : editorial_premium 1.00, editorial_health 0.90, specialized 0.85, retailer 0.60, reference 0.40, ugc 0.30, corporate 0.20, institutional 0.20, competitor 0.10.
6. Bucket : HIGH ≥ 5.0, MEDIUM ≥ 1.5, sinon LOW.
7. Résoudre chaque `brand_id` cité en nom via `list_brands`.
8. Générer l'action recommandée par typologie.
9. Export CSV.

## MCP tools mobilisés

- Peec AI MCP : `get_domain_report` (avec filter prompt_id + dimensions), `list_brands`
- Ahrefs MCP : `site-explorer-domain-rating` (1 call par domaine)
- Optionnel pour typologie fine : classification via Claude (prompt court)

## Notes d'implémentation

- Les `mentioned_brand_ids` sont retournés par Peec dans chaque row de `get_domain_report` — c'est ce qui rend la gap analysis possible sans traverser tous les chats individuellement.
- Enrichissement Ahrefs : batcher les appels DR par vagues de 5 pour éviter les stream timeouts. Expected cost ≈ 2 units per call.
- La whitelist typologique vit dans `peec_brain/citation_authority.py` (`_EDITORIAL_PREMIUM`, `_EDITORIAL_HEALTH`, `_SPECIALIZED_BEAUTY`, `_RETAILERS`, `_UGC`, `_REFERENCE`). À enrichir par secteur client.
- Conserver `peec_classification` en output : sert de double-check quand la whitelist manque un domaine.

## Validation réelle

Exécuté sur Lancôme · prompt "meilleur sérum anti-âge 2026 selon les dermatologues" → 15 domaines cités par les LLMs sur 30 jours, 11 en GAP (citent des concurrents, jamais Lancôme), 5 HIGH priority : vogue.co.uk (DR 87), today.com (DR 90), forbes.com (DR 94), nymag.com (DR 90), healthline.com (DR 92). Le top target (vogue.co.uk) cite Allies of Skin, Chanel, Dr Dennis Gross, Elemis, SkinCeuticals. CSV livré directement à l'équipe RP.

## Statut

Version 1.0 — fonctionnel sur données réelles Lancôme. Prochaines évolutions : multi-prompt batch (agréger sur un pool de prompts au lieu d'un seul), enrichissement Ahrefs referring-domains pour détecter si l'outreach existant a abouti, tracking dans le temps (même domaine apparaît-il plus souvent mois après mois ?).

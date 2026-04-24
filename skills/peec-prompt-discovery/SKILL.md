---
name: peec-prompt-discovery
description: "Module 1 du plugin Peec Brain. Génère les prompts Peec AI à tracker en fusionnant TROIS sources SEO pour des résultats plus précis qu'aucune source seule ne produit : (1) GSC queries quand ownership disponible, (2) Ahrefs site-explorer-organic-keywords pour la donnée de rank et de trafic, (3) un catalogue produit spécifique au client qui permet de générer des prompts sur des références nommées (ex 'La Vie Est Belle Intense avis') que les tools GSC-only ou keyword-only ne peuvent pas atteindre. Classifie l'intent (informational / commercial / branded / comparison / transactional), reformule en questions naturelles, dédoublonne contre les prompts Peec existants, propose des topics, crée en batch via create_prompts. Dry-run par défaut. Trigger : 'génère mes prompts Peec', 'prompt discovery multi-source', 'fusion GSC + Ahrefs + catalogue pour Peec', 'bootstrap Peec pour [marque]', 'découvre les prompts à tracker sur [domaine]'."
license: Stride Up — Peec Brain plugin
---

# peec-prompt-discovery

## Quand l'utiliser

Dès qu'un nouveau client arrive dans le portefeuille Peec et qu'on a besoin de peupler son compte avec des prompts pertinents — ou périodiquement (mensuel) pour enrichir les prompts trackés en fonction de l'évolution des keywords du domaine.

## Inputs attendus

- `domain` (str, requis) : domaine du client (ex. "lancome.com")
- `peec_project_id` (str, requis) : ID du projet Peec cible
- `min_volume` (int, default 100) : volume de recherche minimum pour qu'un keyword Ahrefs soit retenu
- `max_prompts` (int, default 30) : nombre max de prompts à créer en une passe
- `dry_run` (bool, default true) : si true, liste les candidats sans créer dans Peec

## Outputs

- Si `dry_run=true` : CSV `prompt_candidates.csv` avec colonnes [query, volume, intent, topic_suggested, status]
- Si `dry_run=false` : les prompts sont créés dans Peec, ID retournés, + CSV d'audit

## Pipeline

1. Lister les prompts Peec existants (`list_prompts`) pour le projet cible
2. Récupérer les top keywords organic Ahrefs du domaine (`site-explorer-organic-keywords`)
3. Filtrer par volume minimum et dédupliquer
4. Reformuler chaque keyword en question naturelle (template LLM ou règles)
5. Classer par intent : informational / commercial / branded
6. Matcher contre les topics Peec existants ou créer de nouveaux topics
7. Dédoublonner contre les prompts Peec existants (similarité string + embeddings)
8. Batch create : `create_topics` puis `create_prompts` par groupes de 5

## MCP tools mobilisés

- Peec AI MCP : `list_projects`, `list_topics`, `list_prompts`, `create_topics`, `create_prompts`
- Ahrefs MCP : `site-explorer-organic-keywords`, `keywords-explorer-matching-terms`

## Notes d'implémentation

- Rate limits : batch de 5 prompts maximum par appel, sleep 1s entre batches
- La reformulation "query → question" peut utiliser un simple template : "Qu'est-ce que [X] ?", "Comment [Y] ?", "Meilleur [Z]" selon l'intent
- Pour les marques multilingues, filtrer les keywords par `country_code` (FR par défaut)

## Statut

Version 0.1 — squelette. À compléter une fois client vitrine confirmé.

---
name: peec-structural-audit
description: "Module 3 du plugin Peec Brain — LE DIFFÉRENCIATEUR. Répond à 'pourquoi ChatGPT ne cite pas ma page quand il cite celles de mes concurrents' en deux couches structurelles qu'aucun autre outil de l'écosystème Peec n'aligne aujourd'hui. Layer A — structure éditoriale : parse Peec get_url_content pour mesurer densité H2/H3, ingrédients actifs nommés, citations d'experts (MD FAAD DO), tables comparatives, sections standardisées par produit, TOC / ancres, signaux 'how we tested' + 'meet the experts'. Layer B — structure technique schema.org : parse le HTML brut via extruct pour compter la présence des types JSON-LD que les pages citées shippent (Product, AggregateRating, Review, FAQPage, HowTo, BreadcrumbList, Article, Organization) vs la page marque. Diff = signaux présents sur la majorité des pages citées mais absents sur la page marque. Output un brief markdown + JSON avec verdict + gaps éditoriaux + gaps schema + actions prescriptives. Trigger : 'pourquoi ma page n'est pas citée par ChatGPT', 'structural audit de ma page vs concurrents', 'diff schema page marque vs pages citées', 'structural audit [prompt]', 'pourquoi les LLMs me snobent sur [prompt]', 'content brief AI-ready', 'comparatif structurel page marque vs LLM-cited pages'."
license: Stride Up — Peec Brain plugin
---

# peec-structural-audit

## Quand l'utiliser

Pour chaque prompt où la marque est en faible visibility dans Peec et où le Gap Analyzer (Module 2) a déjà identifié une page cible : le Structural Audit donne la réponse à la question suivante, que personne d'autre ne traite — *pourquoi* cette page spécifique n'est-elle pas citée ?

## Inputs attendus

- `prompt_id` (str, requis) : ID du prompt Peec à analyser
- `peec_project_id` (str, requis)
- `brand_target_url` (str, requis) : URL de la page marque à auditer (typiquement issue du Gap Analyzer)
- `n_cited_urls` (int, default 5) : nombre de pages LLM-citées à utiliser comme référence
- `run_layer_b` (bool, default true) : si false, skip l'audit schema (pour environnements sans accès réseau)

## Outputs

- `structural_audit_<prompt_id>.md` — brief markdown humain lisible, partageable en tant que livrable rédacteur/dev
- `structural_audit_<prompt_id>.json` — structure exploitable en aval
- Schéma JSON :
  - `prompt_text`, `brand_url`
  - `brand_audit` : editorial (h2_count, ingredient_mentions, expert_quote_count, ...) + schema (jsonld_types, has_product, has_aggregate_rating, ...)
  - `cited_audits` : même structure × N pages citées
  - `editorial_gaps` : list[str] humainement lisibles
  - `schema_gaps` : list[str]
  - `prescriptive_actions` : list[str]
  - `verdict` : str

## Pipeline

1. Résoudre le prompt_id → `get_chat` + `list_chats` pour extraire les URL effectivement citées (Peec `get_url_report` filtré par prompt_id est le chemin recommandé).
2. `get_url_content` sur chaque URL citée + sur l'URL marque → contenu markdown extrait par Peec.
3. **Layer A (éditorial)** : parse le markdown avec regex pour chaque signal. Pas de dépendance réseau.
4. **Layer B (schema)** : fetch le HTML brut de chaque URL (via requests ou via `scripts/fetch_and_audit.py` standalone si sandbox). Parse via `extruct` → extraction JSON-LD / microdata / RDFa / Open Graph.
5. Agrège : moyenne / ratio par signal sur les pages citées.
6. Diff : emit un gap si le signal est présent sur ≥ 50% des pages citées mais absent sur la page marque.
7. Génère les actions prescriptives + verdict.

## MCP tools mobilisés

- Peec AI MCP : `list_chats`, `get_chat`, `get_url_content`, `get_url_report`
- Dépendance Python : `extruct`, `requests`, `w3lib`

## Notes d'implémentation

- Peec `get_url_content` renvoie du markdown processé via Mozilla Readability, ce qui strip les balises `<script type="application/ld+json">`. Layer B doit donc fetcher le HTML brut séparément.
- Un script standalone `scripts/fetch_and_audit.py` est fourni pour environnements bloqués (Cowork sandbox) : il fait le fetch + extruct offline, produit un JSON exploitable par ce skill en mode `--schema-from`.
- Filtres anti-faux-positif sur les patterns d'expert quotes : exclut les mentions de type "Dr Jart" (nom de marque) vs "Dr Jenny Liu, MD FAAD" (véritable expert).
- La classification URL de Peec (`HOMEPAGE`, `CATEGORY_PAGE`, `PRODUCT_PAGE`, `LISTICLE`, `COMPARISON`, etc.) est conservée dans l'output et utilisée pour ajuster le verdict — une CATEGORY_PAGE sans contenu substantiel est diagnosticablement différente d'un LISTICLE mal structuré.

## Validation réelle

Exécuté sur Lancôme · prompt "meilleur sérum anti-âge 2026 selon les dermatologues" (0% visibility) → diagnostic généré : 3 gaps éditoriaux + 4 gaps schema + 7 actions prescriptives. Verdict : la page catégorie Lancôme n'a ni H2, ni ingrédient actif nommé, ni expert cité, ni Product/AggregateRating/Review/Article JSON-LD, alors que 3/3 pages citées (Vogue FR, Healthline, Vogue UK) ont toutes l'Article + au moins 2 types Product-family.

## Statut

Version 1.0 — fonctionnel sur données réelles Lancôme. Prochaines évolutions : fetch automatique du HTML brut (actuellement via script standalone), support multi-prompts en batch, génération d'un composite "content brief" en un seul appel.

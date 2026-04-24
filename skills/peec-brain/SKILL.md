---
name: peec-brain
description: "Orchestrateur du plugin Peec Brain pour agences SEO et annonceurs pilotant la visibilité AI search. Chaîne les quatre sous-skills en matrice 2x2 (page × source / quoi × pourquoi) : peec-prompt-discovery pour générer les prompts à tracker (fusion GSC + Ahrefs + catalogue produit), peec-gap-analyzer pour prioriser les pages à optimiser (traffic-first), peec-structural-audit pour diagnostiquer pourquoi les pages ne sont pas citées (éditorial + schema.org), peec-citation-authority pour lister les domaines qui citent les concurrents mais jamais la marque (outreach-ready CSV). Exécute en mode onboarding (nouveau client — pipeline complet), weekly (revue hebdo — skip discovery), adhoc (audit ponctuel). Trigger : 'lance Peec Brain', 'onboarding AI visibility pour [client]', 'pipeline Peec Brain complet', 'Peec Brain weekly sur [marque]', 'audit AI visibility complet sur [prompt]'."
license: Stride Up — Peec Brain plugin
---

# peec-brain

## Quand l'utiliser

Point d'entrée unique du plugin. Trois modes :

- **Mode onboarding** : nouveau client dans le portefeuille → pipeline complet 1 → 2 → 3 → 4
- **Mode weekly** : revue hebdomadaire sur un compte actif → skip Module 1 (prompts déjà créés), run Modules 2 → 3 → 4
- **Mode adhoc** : audit ponctuel sur un prompt spécifique → run Modules 3 + 4 uniquement, pour un prompt donné

## Inputs attendus

- `domain` (str, requis)
- `peec_project_id` (str, requis)
- `own_brand_id` (str, requis) : le `is_own=true` brand_id du client
- `client_name` (str, requis)
- `mode` (str, default "weekly") : `"onboarding"` | `"weekly"` | `"adhoc"`
- `target_prompts` (list[str], optional) : prompts à cibler en mode adhoc. En weekly, défaut = tous les prompts à visibility < 30%.
- `schedule_weekly` (bool, default false) : si true, crée un scheduled task via `anthropic-skills:schedule`

## Outputs par mode

| Mode | M1 | M2 | M3 | M4 | Artifact |
|---|---|---|---|---|---|
| onboarding | ✓ create | ✓ | ✓ top 3 prompts | ✓ | ✓ créer |
| weekly | — | ✓ | ✓ top 3 new gaps | ✓ delta | ✓ update |
| adhoc | — | — | ✓ 1 prompt | ✓ 1 prompt | — |

Fichiers produits :
- `prompts_created.csv` (onboarding) — sortie Module 1
- `content_gaps.csv` — sortie Module 2
- `structural_audit_<prompt>.md` + `.json` — sortie Module 3 par prompt
- `citation_authority_<prompt>.csv` — sortie Module 4 par prompt
- URL artifact Cowork rafraîchissable

## Pipeline détaillé

### Mode onboarding (nouveau client)

1. `peec-prompt-discovery` avec `dry_run=false` → crée 20-30 prompts + 5-6 topics
2. Attendre 24h de collecte Peec (ou skip pour démo live)
3. `peec-gap-analyzer` → CSV des 20 pages prioritaires
4. Pour les 3 prompts avec plus grande priorité (0% visibility + fort trafic) :
   - `peec-structural-audit` → brief par prompt
   - `peec-citation-authority` → CSV RP par prompt
5. `peec-radar-artifact` en création → URL livrable client

### Mode weekly (revue hebdo)

1. `peec-gap-analyzer` → détecte les nouveaux gaps
2. Pour les 3 prompts où la visibility a chuté :
   - `peec-structural-audit`
   - `peec-citation-authority`
3. `peec-radar-artifact` update
4. Si `schedule_weekly=true`, planifie la prochaine itération

### Mode adhoc (audit single-prompt)

1. `peec-structural-audit` sur le prompt cible
2. `peec-citation-authority` sur le même prompt
3. Retourne brief + CSV outreach en un seul pass

## Skills dépendants

- `peec-prompt-discovery` (Module 1)
- `peec-gap-analyzer` (Module 2)
- `peec-structural-audit` (Module 3)
- `peec-citation-authority` (Module 4)
- `peec-radar-artifact` (optionnel — pour l'output client)
- `anthropic-skills:schedule` (optionnel — pour le mode weekly automatisé)

## Notes d'implémentation

- Chaque sous-skill est appelable indépendamment ; ce skill les chaîne mais ne duplique pas leur logique
- Ordre de priorité d'exécution en cas de budget limité : M3 > M4 > M2 > M1 (le plus différenciant d'abord)
- Gestion d'erreurs : si M3 échoue sur un prompt (ex : pas de chats disponibles), passer au prompt suivant sans bloquer M4
- Logging explicite à chaque transition entre modules
- Suggestion E-E-A-T : inclure un résumé exécutif en fin de run qui récapitule "3 gaps majeurs + 5 domaines HIGH pour outreach"

## Statut

Version 1.0 — 4 modules opérationnels sur données réelles Lancôme. Orchestrateur conceptuel, Cowork chaîne les skills à la demande. Version 2.0 prévue avec orchestration Python directe (CLI `peec-brain run --mode weekly --project ...`).

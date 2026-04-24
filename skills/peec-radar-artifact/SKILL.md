---
name: peec-radar-artifact
description: "Crée ou met à jour un artifact Cowork 'Peec Brain Radar' qui consolide dans une interface rafraîchissable les trois outputs du gap analyzer (content gaps, digital PR, competitor wins). L'artifact appelle les MCP Peec et Ahrefs à chaque ouverture pour afficher des données fraîches. Utilisable en livrable agence auprès des clients. Trigger : 'crée mon radar Peec', 'dashboard Peec Brain', 'artifact AI visibility', 'livrable client Peec', 'radar hebdo Peec', 'mets à jour le radar Peec'."
license: Stride Up — Peec Brain plugin
---

# peec-radar-artifact

## Quand l'utiliser

Après un run du gap-analyzer, pour matérialiser les 3 outputs dans un artifact Cowork persistant et rafraîchissable. L'artifact devient le livrable hebdomadaire consommable par les équipes SEO ou envoyé au client.

## Inputs attendus

- `domain` (str, requis) : domaine client
- `peec_project_id` (str, requis)
- `client_name` (str, requis) : pour l'en-tête de l'artifact
- `gap_analyzer_output` (path ou dict) : résultat du skill peec-gap-analyzer
- `branding` (dict, optional) : `{logo_url, primary_color, secondary_color}`

## Outputs

- URL de l'artifact Cowork créé (persistant, partageable)
- Mode update : met à jour l'artifact existant sans recréer

## Structure de l'artifact

Trois onglets :
- **Content Gaps** : tableau filtrable des pages à optimiser, colonne priority_score en gradient
- **Digital PR** : tableau des domaines à contacter + cartes domaine avec DR / citations
- **Competitor Wins** : timeline des pages concurrentes gagnantes + suggestions d'action

En en-tête : nom client, date de dernière actualisation, bouton "Refresh from Peec".
En pied : #BuiltWithPeec + logo Stride Up.

## Refresh mechanism

L'artifact appelle `window.cowork.callMcpTool()` pour relancer les MCP Peec et Ahrefs à la demande. Exemple :

```js
const chats = await window.cowork.callMcpTool('peec:list_chats', { project_id, limit: 100 });
// Recalcul des 3 outputs en JS côté artifact
```

## MCP tools mobilisés

- Cowork : `create_artifact`, `update_artifact`
- À l'exécution dans l'artifact : `list_chats`, `list_prompts`, `get_domain_report`, `site-explorer-*`, `brand-radar-*`

## Notes design

- Palette : navy #1F2A44 / blue #2E75B6 / light #D5E8F0 / grey #F2F2F2
- Typography : system-ui (pas de webfont)
- Responsive : colonne unique sous 768px
- Pas de framework CSS (évite les dépendances)

## Statut

Version 0.1 — squelette. Template HTML à construire en Phase 4.

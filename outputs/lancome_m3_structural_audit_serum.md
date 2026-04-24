# Structural Audit — Module 3

**Prompt** : Quel est le meilleur sérum anti-âge en 2026 selon les dermatologues ?
**Page marque** : https://lancome.fr/soin/par-categorie/serum-visage
**Pages citées analysées** : 3

## Verdict

Gaps structurels majeurs détectés : 3 éditorial(aux), 4 schema. Les LLMs ne trouvent pas le signal attendu sur la page marque — ils se rabattent sur les 3 pages éditoriales citées.

## Layer A — Gaps éditoriaux (page marque vs majorité des pages citées)

- Structure H2 : la page marque a 0 H2 contre une moyenne de 4.3 sur les pages citées. Les LLMs privilégient les pages structurées (5+ H2 minimum).
- Couverture ingrédients : 0 ingrédients actifs nommés contre une moyenne de 13.7 sur les pages citées. Les LLMs raisonnent par ingrédient actif ; une page qui ne les nomme pas est invisible.
- Experts cités : 100% des pages citées contiennent des citations de dermatologues (MD, FAAD, DO). La page marque n'en a aucune.

## Layer B — Gaps de données structurées (schema.org)

- Schema `Product` : présent sur 3/3 pages citées, absent sur la page marque.
- Schema `AggregateRating` : présent sur 3/3 pages citées, absent sur la page marque.
- Schema `Review` : présent sur 2/3 pages citées, absent sur la page marque.
- Schema `Article` : présent sur 3/3 pages citées, absent sur la page marque.

## Actions prescriptives

1. Ajouter au moins 4 sections H2 substantielles sur la page cible.
2. Nommer explicitement les ingrédients actifs dans le contenu : acide hyaluronique, ascorbate, azelaic, ceramide, collagen, collagene, collagène, céramide.
3. Inclure 1-2 citations de dermatologues experts (avec crédibilité MD/FAAD explicitement visible) sur la formulation des actifs clés.
4. Implémenter JSON-LD `Product` sur les pages produit/catégorie.
5. Exposer `AggregateRating` (note + nombre d'avis) en JSON-LD.
6. Intégrer `Review` JSON-LD pour les avis produits.
7. Restructurer la page comme `Article` avec auteur/date/reviewedBy visible en JSON-LD.

## Comparatif par page

| URL | Citation rate | Type | H2 | Ingrédients | Experts | Table | JSON-LD types |
|---|---|---|---|---|---|---|---|
| lancome.fr/soin/par-categorie/serum-visage | 0.00 | CATEGORY_PAGE | 0 | 0 | 0 | — | BreadcrumbList, ListItem, Organization, WebPage |
| vogue.fr/beaute/article/meilleurs-serums-anti-age | 0.36 | LISTICLE | 11 | 12 | 1 | — | AggregateRating, Article, BreadcrumbList, ListItem, Organization, Person, Product, Rating, Review |
| healthline.com/health/beauty-skin-care/best-anti-a | 1.00 | LISTICLE | 0 | 17 | 1 | ✓ | AggregateRating, Answer, Article, BreadcrumbList, FAQPage, ItemList, ListItem, Offer, Organization, Person, Product, Question |
| vogue.co.uk/article/best-anti-ageing-serums | 0.88 | LISTICLE | 2 | 12 | 2 | — | AggregateRating, Article, BreadcrumbList, ListItem, Organization, Person, Product, Rating, Review |
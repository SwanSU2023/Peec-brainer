"""Module 3 — Structural Audit (editorial + schema).

Diagnoses why a brand page isn't cited when competitor pages are, along
two axes:

Layer A — Editorial structure. Works on Peec get_url_content markdown
          (or any markdown-extracted content). Measures:
            - H2/H3 section density
            - Named active ingredient coverage
            - Expert quote presence (dermatologist, MD, FAAD, DO, etc.)
            - Comparison table presence
            - Standardised per-product block structure
            - TOC/anchor navigation
            - "How we tested" / "Meet the experts" signals

Layer B — Technical structure (schema.org). Works on raw HTML via
          `extruct`. Measures presence of:
            - JSON-LD types: Product, AggregateRating, Review, FAQPage,
              HowTo, BreadcrumbList, Article, Organization
            - Microdata / RDFa / Open Graph coverage

Layer B requires raw HTML, which Peec's get_url_content strips. To run
Layer B end-to-end, fetch the pages with `requests` (outside network-
restricted environments) and feed the HTML into `extract_schema_types`.

Diff logic: for each signal present on a majority of cited pages but
absent on the brand page, emit a prescriptive action.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------- Data models ----------


@dataclass
class EditorialSignals:
    """Editorial structure signals from markdown content."""
    h2_count: int
    h3_count: int
    word_count: int
    ingredient_mentions: list[str]
    expert_quote_count: int
    expert_names: list[str]
    comparison_table_count: int
    per_product_block_signals: list[str]  # ["Key ingredients", "Best for", ...]
    has_toc: bool
    has_how_we_tested: bool
    has_meet_the_experts: bool
    has_skin_type_sections: bool
    has_application_sections: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SchemaSignals:
    """JSON-LD / microdata / Open Graph signals from raw HTML."""
    jsonld_types: list[str]            # e.g. ["Product", "AggregateRating"]
    microdata_types: list[str]
    rdfa_types: list[str]
    opengraph_present: bool
    has_product: bool
    has_aggregate_rating: bool
    has_review: bool
    has_faq_page: bool
    has_how_to: bool
    has_breadcrumb: bool
    has_article: bool
    has_organization: bool

    @classmethod
    def empty(cls) -> "SchemaSignals":
        return cls(
            jsonld_types=[], microdata_types=[], rdfa_types=[],
            opengraph_present=False, has_product=False, has_aggregate_rating=False,
            has_review=False, has_faq_page=False, has_how_to=False,
            has_breadcrumb=False, has_article=False, has_organization=False,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageAudit:
    """Combined audit for one page."""
    url: str
    title: str
    url_classification: str
    editorial: EditorialSignals
    schema: SchemaSignals
    is_cited: bool           # was this page cited by LLMs (vs brand target)
    citation_count: int = 0
    retrieval_count: int = 0
    citation_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "url_classification": self.url_classification,
            "editorial": self.editorial.to_dict(),
            "schema": self.schema.to_dict(),
            "is_cited": self.is_cited,
            "citation_count": self.citation_count,
            "retrieval_count": self.retrieval_count,
            "citation_rate": self.citation_rate,
        }


@dataclass
class StructuralDiff:
    """The output: what the brand page lacks vs cited pages."""
    prompt_text: str
    brand_url: str
    brand_audit: PageAudit
    cited_audits: list[PageAudit]
    editorial_gaps: list[str]        # human-readable
    schema_gaps: list[str]           # human-readable
    prescriptive_actions: list[str]
    verdict: str

    def to_dict(self) -> dict:
        return {
            "prompt_text": self.prompt_text,
            "brand_url": self.brand_url,
            "brand_audit": self.brand_audit.to_dict(),
            "cited_audits": [a.to_dict() for a in self.cited_audits],
            "editorial_gaps": self.editorial_gaps,
            "schema_gaps": self.schema_gaps,
            "prescriptive_actions": self.prescriptive_actions,
            "verdict": self.verdict,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Structural Audit — Module 3",
            "",
            f"**Prompt**: {self.prompt_text}",
            f"**Brand page**: {self.brand_url}",
            f"**Cited pages analysed**: {len(self.cited_audits)}",
            "",
            "## Verdict",
            "",
            self.verdict,
            "",
            "## Layer A — Editorial gaps (brand page vs majority of cited pages)",
            "",
        ]
        if self.editorial_gaps:
            for g in self.editorial_gaps:
                lines.append(f"- {g}")
        else:
            lines.append("- No significant editorial gap detected.")

        lines.extend([
            "",
            "## Layer B — Structured-data gaps (schema.org)",
            "",
        ])
        if self.schema_gaps:
            for g in self.schema_gaps:
                lines.append(f"- {g}")
        else:
            lines.append("- No schema gap detected (or schema audit not executed).")

        lines.extend([
            "",
            "## Prescriptive actions",
            "",
        ])
        for i, a in enumerate(self.prescriptive_actions, start=1):
            lines.append(f"{i}. {a}")

        lines.extend([
            "",
            "## Per-page comparison",
            "",
            "| URL | Citation rate | Type | H2 | Ingredients | Experts | Table | JSON-LD types |",
            "|---|---|---|---|---|---|---|---|",
        ])
        all_audits = [self.brand_audit] + self.cited_audits
        for a in all_audits:
            short_url = a.url.replace("https://www.", "").replace("https://", "")[:50]
            types = ", ".join(a.schema.jsonld_types) if a.schema.jsonld_types else "(not audited)"
            table_mark = "✓" if a.editorial.comparison_table_count > 0 else "—"
            lines.append(
                f"| {short_url} | {a.citation_rate:.2f} | {a.url_classification} | "
                f"{a.editorial.h2_count} | {len(a.editorial.ingredient_mentions)} | "
                f"{a.editorial.expert_quote_count} | {table_mark} | {types} |"
            )

        return "\n".join(lines)


# ---------- Internals ----------


_WS = re.compile(r"\s+")
_H2_RE = re.compile(r"^##\s+.+$", re.MULTILINE)
_H3_RE = re.compile(r"^###\s+.+$", re.MULTILINE)

# French + English active ingredients commonly referenced in anti-age content
_INGREDIENT_KEYWORDS = [
    "retinol", "rétinol", "retinal", "rétinal", "retinoide", "rétinoïde",
    "acide hyaluronique", "hyaluronic acid",
    "vitamine c", "vitamin c", "ascorbic", "ascorbate",
    "peptide", "peptides",
    "niacinamide",
    "ceramide", "céramide",
    "collagene", "collagène", "collagen",
    "squalane",
    "resveratrol", "resvératrol",
    "glycolique", "glycolic",
    "salicylique", "salicylic",
    "azelaic", "azélaïque",
    "tripeptide", "hexapeptide", "octapeptide",
    "glutathione", "glutathion",
    "ergothioneine", "ergothionéine",
]

_EXPERT_QUOTE_PATTERNS = [
    # "Dr Name" or "Dr. Name" followed by sentence
    r"(?:Dr\.?|Doctor|Docteure?)\s+[A-ZÀ-Ö][a-zà-ö]+(?:\s+[A-ZÀ-Ö][a-zà-ö]+)?",
    # "Name, MD" or "Name, FAAD" or "Name, DO" etc.
    r"[A-ZÀ-Ö][a-zà-ö]+(?:\s+[A-ZÀ-Ö][a-zà-ö]+)?,\s*(?:MD|FAAD|DO|MS|PhD|FRCP)",
    # "dermatologist Dr ..."
    r"dermatolog(?:ist|ue)s?\s+Dr",
    # Quoted sections
    r'[""]([^"""]{20,200})[""]\s*(?:says?|explique|selon|explains|adds?)',
]

_COMPARISON_TABLE_PATTERN = re.compile(
    r"^\s*\|.+\|.+\|\s*$\n\s*\|[-\s|:]+\|\s*$", re.MULTILINE
)

_PER_PRODUCT_BLOCK_MARKERS = [
    # French
    "Actifs clés", "Actif clé", "Type de peau", "Application",
    "Prix", "Format",
    # English
    "Key ingredients", "Best for", "Skin type", "When to use",
    "Editor's experience", "Why it's",
]


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _fold(s: str) -> str:
    return _strip_accents(s).lower().strip()


# ---------- Layer A — Editorial audit ----------


def extract_editorial_signals(content: str) -> EditorialSignals:
    """Parse markdown/text content and extract structural signals."""
    content = content or ""
    content_fold = _fold(content)

    h2_count = len(_H2_RE.findall(content))
    h3_count = len(_H3_RE.findall(content))
    word_count = len(_WS.split(content.strip())) if content.strip() else 0

    # Ingredient mentions (dedupe, case-insensitive, accent-insensitive)
    ingredients = set()
    for kw in _INGREDIENT_KEYWORDS:
        if _fold(kw) in content_fold:
            ingredients.add(kw.lower())

    # Expert quotes: count distinct expert references
    expert_matches = set()
    for pat in _EXPERT_QUOTE_PATTERNS:
        for m in re.finditer(pat, content):
            expert_matches.add(m.group(0).strip())
    # Filter out false positives (stray "Dr Jart", "Dr Pepper" brand names)
    filtered_experts = [
        e for e in expert_matches
        if not re.search(r"(?:Dr\s+Jart|Dr\s+Pepper|Dr\s+Martens)", e, re.IGNORECASE)
    ]
    expert_count = len(filtered_experts)

    table_count = len(_COMPARISON_TABLE_PATTERN.findall(content))

    # Per-product block signals
    per_product_signals = []
    for marker in _PER_PRODUCT_BLOCK_MARKERS:
        if marker.lower() in content.lower():
            per_product_signals.append(marker)

    return EditorialSignals(
        h2_count=h2_count,
        h3_count=h3_count,
        word_count=word_count,
        ingredient_mentions=sorted(ingredients),
        expert_quote_count=expert_count,
        expert_names=sorted(filtered_experts)[:10],
        comparison_table_count=table_count,
        per_product_block_signals=per_product_signals,
        has_toc=bool(re.search(r"(jump to|in this article|table of contents|sommaire|dans cet article)",
                                content, re.IGNORECASE)),
        has_how_we_tested=bool(re.search(r"(how we tested|comment nous avons test|notre méthodo)",
                                          content, re.IGNORECASE)),
        has_meet_the_experts=bool(re.search(r"(meet the experts|nos experts|our experts)",
                                             content, re.IGNORECASE)),
        has_skin_type_sections=bool(re.search(r"(type de peau|skin type|peaux sensibles|peaux mixtes)",
                                              content, re.IGNORECASE)),
        has_application_sections=bool(re.search(r"(application\s*:|when to use|matin et soir|morning and evening)",
                                                 content, re.IGNORECASE)),
    )


# ---------- Layer B — Schema audit (via extruct on raw HTML) ----------


def extract_schema_types(raw_html: Optional[str]) -> SchemaSignals:
    """Parse raw HTML with extruct to extract schema.org types.

    Returns empty signals if raw_html is None (e.g. when we only have
    Peec's processed content, not raw HTML).
    """
    if not raw_html:
        return SchemaSignals.empty()

    try:
        import extruct
        from w3lib.html import get_base_url
    except ImportError:
        return SchemaSignals.empty()

    base = get_base_url(raw_html, "")
    data = extruct.extract(
        raw_html,
        base_url=base,
        syntaxes=["json-ld", "microdata", "rdfa", "opengraph"],
    )

    jsonld_types = _collect_types_from_jsonld(data.get("json-ld", []))
    microdata_types = _collect_types_from_microdata(data.get("microdata", []))
    rdfa_types = _collect_types_from_rdfa(data.get("rdfa", []))
    og = bool(data.get("opengraph"))

    def _has(type_name: str) -> bool:
        name_l = type_name.lower()
        return any(name_l in t.lower() for t in jsonld_types + microdata_types + rdfa_types)

    return SchemaSignals(
        jsonld_types=sorted(set(jsonld_types)),
        microdata_types=sorted(set(microdata_types)),
        rdfa_types=sorted(set(rdfa_types)),
        opengraph_present=og,
        has_product=_has("product"),
        has_aggregate_rating=_has("aggregaterating"),
        has_review=_has("review"),
        has_faq_page=_has("faqpage"),
        has_how_to=_has("howto"),
        has_breadcrumb=_has("breadcrumb"),
        has_article=_has("article"),
        has_organization=_has("organization"),
    )


def _collect_types_from_jsonld(items: list) -> list[str]:
    types: list[str] = []
    def _walk(obj):
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend([x for x in t if isinstance(x, str)])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
    for it in items:
        _walk(it)
    return types


def _collect_types_from_microdata(items: list) -> list[str]:
    types: list[str] = []
    for it in items:
        t = it.get("type") if isinstance(it, dict) else None
        if isinstance(t, str):
            types.append(t.rsplit("/", 1)[-1])
        elif isinstance(t, list):
            types.extend([x.rsplit("/", 1)[-1] for x in t if isinstance(x, str)])
    return types


def _collect_types_from_rdfa(items: list) -> list[str]:
    types: list[str] = []
    for it in items:
        t = it.get("@type") if isinstance(it, dict) else None
        if isinstance(t, list):
            types.extend([x for x in t if isinstance(x, str)])
        elif isinstance(t, str):
            types.append(t)
    return types


# ---------- Public API ----------


def audit_page(
    *,
    url: str,
    title: str,
    url_classification: str,
    content_markdown: str,
    raw_html: Optional[str] = None,
    is_cited: bool = False,
    citation_count: int = 0,
    retrieval_count: int = 0,
    citation_rate: float = 0.0,
) -> PageAudit:
    """Audit one page across both layers."""
    return PageAudit(
        url=url,
        title=title,
        url_classification=url_classification,
        editorial=extract_editorial_signals(content_markdown),
        schema=extract_schema_types(raw_html),
        is_cited=is_cited,
        citation_count=citation_count,
        retrieval_count=retrieval_count,
        citation_rate=citation_rate,
    )


def structural_audit(
    prompt_text: str,
    brand_page: PageAudit,
    cited_pages: list[PageAudit],
    majority_threshold: float = 0.5,
) -> StructuralDiff:
    """Diff brand page vs the majority of cited pages, emit actions."""
    editorial_gaps: list[str] = []
    schema_gaps: list[str] = []
    actions: list[str] = []

    n = len(cited_pages)
    if n == 0:
        return StructuralDiff(
            prompt_text=prompt_text,
            brand_url=brand_page.url,
            brand_audit=brand_page,
            cited_audits=cited_pages,
            editorial_gaps=["Aucune page citée à comparer."],
            schema_gaps=[],
            prescriptive_actions=[],
            verdict="Audit not executable — no reference pages to compare against.",
        )

    # --- Editorial gaps ---
    avg_h2 = sum(p.editorial.h2_count for p in cited_pages) / n
    avg_ingredients = sum(len(p.editorial.ingredient_mentions) for p in cited_pages) / n
    tables_present_ratio = sum(1 for p in cited_pages if p.editorial.comparison_table_count > 0) / n
    experts_present_ratio = sum(1 for p in cited_pages if p.editorial.expert_quote_count > 0) / n
    toc_ratio = sum(1 for p in cited_pages if p.editorial.has_toc) / n
    tested_ratio = sum(1 for p in cited_pages if p.editorial.has_how_we_tested) / n

    if brand_page.editorial.h2_count < avg_h2 * 0.5:
        editorial_gaps.append(
            f"H2 structure: the brand page has {brand_page.editorial.h2_count} H2s "
            f"against an average of {avg_h2:.1f} on cited pages. "
            "LLMs favour structured pages (5+ H2s minimum)."
        )
        actions.append(
            f"Add at least {int(avg_h2) - brand_page.editorial.h2_count} substantive "
            "H2 sections on the target page."
        )

    if len(brand_page.editorial.ingredient_mentions) < avg_ingredients * 0.5:
        editorial_gaps.append(
            f"Ingredient coverage: {len(brand_page.editorial.ingredient_mentions)} active "
            f"ingredients named on the brand page against an average of {avg_ingredients:.1f} "
            "on cited pages. LLMs reason by active ingredient — a page that doesn't name "
            "them is invisible."
        )
        missing_ingredients = set()
        for p in cited_pages:
            missing_ingredients.update(p.editorial.ingredient_mentions)
        missing_ingredients -= set(brand_page.editorial.ingredient_mentions)
        if missing_ingredients:
            top_missing = sorted(missing_ingredients)[:8]
            actions.append(
                "Explicitly name active ingredients in the copy: "
                f"{', '.join(top_missing)}."
            )

    if tables_present_ratio >= majority_threshold and brand_page.editorial.comparison_table_count == 0:
        editorial_gaps.append(
            f"Comparison tables: {tables_present_ratio:.0%} of cited pages include one, "
            "the brand page has none. Healthline-style pages use tables mapping "
            "Price × Skin type × Ingredients × Usage."
        )
        actions.append(
            "Add a comparison table covering the range's products with columns: "
            "price, skin type, key ingredients, time of application."
        )

    if experts_present_ratio >= majority_threshold and brand_page.editorial.expert_quote_count == 0:
        editorial_gaps.append(
            f"Expert quotes: {experts_present_ratio:.0%} of cited pages include quotes from "
            "dermatologists (MD, FAAD, DO). The brand page has none."
        )
        actions.append(
            "Include 1-2 dermatologist expert quotes (with MD/FAAD credibility explicitly "
            "visible) on the formulation of the key actives."
        )

    if toc_ratio >= majority_threshold and not brand_page.editorial.has_toc:
        editorial_gaps.append(
            f"Internal navigation: {toc_ratio:.0%} of cited pages have a TOC or 'Jump to' "
            "anchors. The brand page has none — LLMs use these anchors to extract sections."
        )
        actions.append(
            "Add an 'In this article' / 'Jump to' block at the top of the page with "
            "anchors to each H2."
        )

    if tested_ratio >= majority_threshold and not brand_page.editorial.has_how_we_tested:
        editorial_gaps.append(
            f"Testing methodology: {tested_ratio:.0%} of cited pages have a 'How we tested' "
            "section. Strong E-E-A-T signal for LLMs."
        )
        actions.append(
            "Add a 'How we selected these products' section explaining the methodology "
            "behind the featured products."
        )

    # --- Schema gaps ---
    # Map schema.org type name → SchemaSignals attribute name.
    _SCHEMA_ATTR = {
        "Product":         "has_product",
        "AggregateRating": "has_aggregate_rating",
        "Review":          "has_review",
        "FAQPage":         "has_faq_page",
        "HowTo":           "has_how_to",
        "BreadcrumbList":  "has_breadcrumb",
        "Article":         "has_article",
        "Organization":    "has_organization",
    }
    has_any_schema_audit = any(p.schema.jsonld_types for p in cited_pages)

    if has_any_schema_audit:
        type_counts: dict[str, int] = {}
        for p in cited_pages:
            for stype, attr in _SCHEMA_ATTR.items():
                if getattr(p.schema, attr, False):
                    type_counts[stype] = type_counts.get(stype, 0) + 1

        _ACTIONS = {
            "Product":         "Implement JSON-LD `Product` on product and category pages.",
            "AggregateRating": "Expose `AggregateRating` (rating value + review count) in JSON-LD.",
            "Review":          "Add `Review` JSON-LD for individual product reviews.",
            "FAQPage":         "Add an FAQ section with `FAQPage` JSON-LD markup.",
            "HowTo":           "Add a usage-routine section with `HowTo` JSON-LD markup.",
            "BreadcrumbList":  "Add a breadcrumb navigation with `BreadcrumbList` JSON-LD.",
            "Article":         "Restructure the page as `Article` with author, datePublished, and reviewedBy visible in JSON-LD.",
        }
        for stype, count in type_counts.items():
            ratio = count / n
            has_on_brand = getattr(brand_page.schema, _SCHEMA_ATTR[stype], False)
            if ratio >= majority_threshold and not has_on_brand:
                schema_gaps.append(
                    f"Schema `{stype}`: present on {count}/{n} cited pages, absent on the brand page."
                )
                if stype in _ACTIONS:
                    actions.append(_ACTIONS[stype])
    else:
        schema_gaps.append(
            "Layer B (schema) not executed — requires raw HTML of the pages. "
            "Run `python3 scripts/fetch_and_audit.py` outside restricted networks."
        )

    # --- Verdict ---
    if not editorial_gaps and not schema_gaps:
        verdict = (
            "The brand page is structurally comparable to the cited pages. "
            "Investigate other causes: domain authority, content freshness, "
            "or missing author / E-E-A-T signals."
        )
    else:
        n_ed = len(editorial_gaps)
        n_sc = len([s for s in schema_gaps if not s.startswith("Layer B")])
        verdict = (
            f"Major structural gaps detected: {n_ed} editorial, {n_sc} schema. "
            "LLMs do not find the expected signal on the brand page — they fall back "
            f"on the {n} editorial pages cited instead."
        )

    return StructuralDiff(
        prompt_text=prompt_text,
        brand_url=brand_page.url,
        brand_audit=brand_page,
        cited_audits=cited_pages,
        editorial_gaps=editorial_gaps,
        schema_gaps=schema_gaps,
        prescriptive_actions=actions,
        verdict=verdict,
    )

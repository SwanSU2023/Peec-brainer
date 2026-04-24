"""Module 4 — Citation Authority Audit.

Produces an outreach-ready CSV of the domains that LLMs cite when
recommending competitors, but that have never mentioned the own brand.
Each domain is enriched with its Ahrefs Domain Rating, classified into
a typology (editorial / specialized / retailer / UGC / corporate /
reference), and assigned an outreach priority based on citation
frequency × DR × typology weight.

The pitch: "Here are the 25 domains that decided not to talk about
you, and here is who they cite in your place. Your next-quarter PR
campaign starts here."

Data inputs (MCP-native):
  - Peec get_domain_report (prompt_id filter) → citation_count,
    retrieval_count, classification (EDITORIAL / UGC / CORPORATE /
    INSTITUTIONAL / REFERENCE / COMPETITOR / OWN / OTHER),
    mentioned_brand_ids[]
  - Ahrefs site-explorer-domain-rating → DR, ahrefs_rank

Computation is pure here; MCP calls live in the orchestration layer.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from typing import Optional


# ---------- Data models ----------


@dataclass
class BrandRef:
    brand_id: str
    name: str
    is_own: bool = False


@dataclass
class CitedDomain:
    """One row from Peec get_domain_report."""
    domain: str
    classification: str                # EDITORIAL | UGC | CORPORATE | ...
    citation_count: int
    retrieval_count: int
    citation_rate: float
    mentioned_brand_ids: list[str]


@dataclass
class EnrichedDomain:
    """A cited domain with typology + DR enrichment + priority score."""
    domain: str
    peec_classification: str
    typology: str                      # editorial_premium | specialized | retailer | ugc | corporate | reference | other
    domain_rating: Optional[float]
    ahrefs_rank: Optional[int]
    citation_count: int
    retrieval_count: int
    citation_rate: float
    cites_own_brand: bool              # does this domain ever mention the brand?
    cited_competitors: list[str]       # names of competitors mentioned (resolved from brand_ids)
    competitor_count: int
    outreach_priority: str             # HIGH | MEDIUM | LOW
    priority_score: float
    recommended_action: str
    notes: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cited_competitors"] = ", ".join(self.cited_competitors)
        return d


# ---------- Typology classification ----------

# Curated whitelists — expand over time. Regex-safe (lowercased domain match).
_EDITORIAL_PREMIUM = {
    "vogue.fr", "vogue.com", "vogue.co.uk", "vogue.it",
    "elle.fr", "elle.com", "marieclaire.fr", "marieclaire.com",
    "harpersbazaar.com", "harpersbazaar.co.uk",
    "forbes.com", "nymag.com", "newyorker.com",
    "lefigaro.fr", "madame.lefigaro.fr",
    "grazia.fr", "glamourmagazine.co.uk", "glamour.com",
    "cosmopolitan.com", "cosmopolitan.fr",
    "instyle.com", "today.com", "prevention.com",
    "people.com", "femina.fr", "elle.com",
    "refinery29.com", "bustle.com",
    "lexpress.fr", "lemonde.fr", "nytimes.com",
}
_EDITORIAL_HEALTH = {
    "healthline.com", "webmd.com", "medicalnewstoday.com",
    "topsante.com", "sante-magazine.fr", "santemagazine.fr",
    "ma-sante.news", "aufeminin.com",
}
_SPECIALIZED_BEAUTY = {
    "byrdie.com", "allure.com", "paulaschoice.com",
    "into-the-gloss.com", "beautypedia.com",
    "beaute-test.com", "beautyheaven.com.au",
    "avisbeaute.fr", "holiae.com", "aziobeauty.com",
    "nouvojour.fr", "drdesjarlais.com", "salutbonjour.ca",
    "avisverifies.com", "mymedadvisor.com",
}
_RETAILERS = {
    "sephora.com", "sephora.fr", "nocibe.fr",
    "douglas.com", "douglas.fr", "marionnaud.fr",
    "notino.fr", "notino.com", "notino.be",
    "amazon.fr", "amazon.com",
    "feelunique.com", "lookfantastic.com",
    "mankind.co.uk", "cultbeauty.com",
}
_UGC = {
    "reddit.com", "beautylish.com", "makeupalley.com",
    "trustpilot.com", "quora.com", "medium.com",
    "youtube.com", "tiktok.com", "instagram.com",
    "dailymotion.com",
}
_REFERENCE = {
    "wikipedia.org", "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov", "who.int", "fda.gov",
    "ema.europa.eu",
}


def classify_typology(domain: str, peec_classification: str = "") -> str:
    """Map a domain + Peec classification to the outreach typology."""
    d = domain.lower().lstrip(".")
    # Strip "www." for matching
    d_nowww = d[4:] if d.startswith("www.") else d

    if d_nowww in _EDITORIAL_PREMIUM:
        return "editorial_premium"
    if d_nowww in _EDITORIAL_HEALTH:
        return "editorial_health"
    if d_nowww in _SPECIALIZED_BEAUTY:
        return "specialized"
    if d_nowww in _RETAILERS:
        return "retailer"
    if d_nowww in _UGC:
        return "ugc"
    if d_nowww in _REFERENCE:
        return "reference"

    # Fallback on Peec classification
    mapping = {
        "EDITORIAL": "editorial_premium",  # conservative optimism
        "UGC": "ugc",
        "REFERENCE": "reference",
        "CORPORATE": "corporate",
        "INSTITUTIONAL": "institutional",
        "COMPETITOR": "competitor",
        "OWN": "own",
    }
    return mapping.get(peec_classification, "other")


# ---------- Priority scoring ----------


# Higher = more actionable for an agency outreach campaign.
_TYPOLOGY_WEIGHT = {
    "editorial_premium": 1.00,
    "editorial_health":  0.90,
    "specialized":       0.85,
    "retailer":          0.60,
    "reference":         0.40,
    "corporate":         0.20,  # likely a competitor-adjacent property
    "ugc":               0.30,
    "institutional":     0.20,
    "competitor":        0.10,
    "own":               0.0,
    "other":             0.40,
}


def _priority_score(
    citation_count: int,
    retrieval_count: int,
    dr: Optional[float],
    typology: str,
) -> float:
    frequency = citation_count + retrieval_count * 0.3
    authority = (dr / 100.0) if dr is not None else 0.5   # neutral default
    weight = _TYPOLOGY_WEIGHT.get(typology, 0.4)
    return round(frequency * authority * weight, 2)


def _priority_bucket(score: float) -> str:
    if score >= 5.0:
        return "HIGH"
    if score >= 1.5:
        return "MEDIUM"
    return "LOW"


# ---------- Recommended actions ----------


_ACTIONS = {
    "editorial_premium": (
        "Beauty/lifestyle outreach: pitch a hero product with a trend angle and press "
        "samples. Prioritise beauty journalists listed on the masthead."
    ),
    "editorial_health": (
        "Pitch the dermatologist angle: scientific validation, MD expert partnership, "
        "clinical studies on flagship active ingredients."
    ),
    "specialized": (
        "Send products for review plus a technical ingredient briefing. Expect to be "
        "benchmarked against competitors explicitly."
    ),
    "retailer": (
        "Activate the retail partnership: merchandising highlight, incentivised customer "
        "reviews, placement in seasonal buying guides."
    ),
    "ugc": (
        "Community seeding: niche influencers, dermatology creators, forum moderator "
        "partnerships. Not a traditional press pitch."
    ),
    "reference": (
        "Submit studies / white papers when relevant. Long cycle — focus on scientific "
        "authority rather than immediate coverage."
    ),
    "corporate": (
        "Investigate first: likely a competitor-adjacent property. Decide whether to "
        "exclude or handle via indirect PR."
    ),
    "institutional": (
        "Long cycle: submissions to committees, industry conferences, scientific "
        "partnerships."
    ),
    "competitor": (
        "No outreach action. Monitor for benchmarking purposes."
    ),
    "own": "—",
    "other": "Manual qualification required.",
}


# ---------- Public API ----------


def enrich_and_prioritize(
    cited_domains: list[CitedDomain],
    *,
    own_brand_id: str,
    competitors: list[BrandRef],
    domain_ratings: dict[str, dict],       # {domain: {"domain_rating": 82, "ahrefs_rank": 9127}}
) -> list[EnrichedDomain]:
    """Produce the prioritized outreach list.

    Gap list = domains that cite at least one competitor but never the own brand.

    Args:
      cited_domains : list of CitedDomain from Peec get_domain_report.
      own_brand_id  : the `is_own=true` brand's ID.
      competitors   : list of BrandRef to resolve brand_ids → names.
      domain_ratings: per-domain Ahrefs enrichment (optional for each domain).

    Returns:
      list[EnrichedDomain] sorted by priority_score desc, GAP domains only.
    """
    comp_by_id = {c.brand_id: c for c in competitors}
    enriched: list[EnrichedDomain] = []

    for d in cited_domains:
        mentioned_ids = set(d.mentioned_brand_ids)
        cites_own = own_brand_id in mentioned_ids
        competitor_hits = [
            comp_by_id[bid].name for bid in mentioned_ids
            if bid in comp_by_id and not comp_by_id[bid].is_own
        ]

        # A "gap" domain cites competitors but not the own brand
        if cites_own or not competitor_hits:
            continue

        typology = classify_typology(d.domain, d.classification)
        dr_info = domain_ratings.get(d.domain, {}) or {}
        dr = dr_info.get("domain_rating")
        ah_rank = dr_info.get("ahrefs_rank")
        score = _priority_score(d.citation_count, d.retrieval_count, dr, typology)

        n_comp = len(competitor_hits)
        notes_bits = []
        if dr is None:
            notes_bits.append("DR not measured (Ahrefs enrichment pending)")
        if n_comp >= 5:
            notes_bits.append(f"{n_comp} competitors cited — strong editorial competition")
        elif n_comp == 1:
            notes_bits.append(f"Only one competitor cited ({competitor_hits[0]}) — open window")

        enriched.append(EnrichedDomain(
            domain=d.domain,
            peec_classification=d.classification,
            typology=typology,
            domain_rating=dr,
            ahrefs_rank=ah_rank,
            citation_count=d.citation_count,
            retrieval_count=d.retrieval_count,
            citation_rate=d.citation_rate,
            cites_own_brand=False,
            cited_competitors=sorted(set(competitor_hits)),
            competitor_count=n_comp,
            outreach_priority=_priority_bucket(score),
            priority_score=score,
            recommended_action=_ACTIONS.get(typology, "Qualification manuelle requise."),
            notes=" · ".join(notes_bits) if notes_bits else "",
        ))

    enriched.sort(key=lambda e: e.priority_score, reverse=True)
    return enriched


def export_csv(rows: list[EnrichedDomain], out_path) -> None:
    """Write enriched domains to a CSV tailored for PR outreach teams."""
    fieldnames = [
        "domain",
        "typology",
        "outreach_priority",
        "priority_score",
        "domain_rating",
        "ahrefs_rank",
        "citation_count",
        "retrieval_count",
        "citation_rate",
        "competitor_count",
        "cited_competitors",
        "peec_classification",
        "recommended_action",
        "notes",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            d = r.to_dict()
            w.writerow({k: d.get(k, "") for k in fieldnames})

"""Module 2 — Content Gap (traffic-first prioritization).

Positioning vs other challenge submissions:
  - Ritwika's workflow-1, Lukas's content-gap-hunt and the Drift Radar
    silence split all ship variants of "pages with 0% visibility".
  - Our differentiator: we prioritize by EXISTING BUSINESS VALUE, not by
    traffic potential or prompt count. The formula is:
        priority_score = Ahrefs top-page traffic × (1 − AI visibility)
    The signal: a page already earning 1 000+ Google visits/mo but
    invisible in LLMs is where every euro of content optimization work
    should land first.

Three output surfaces (Content Gaps implemented here; Digital PR +
Competitor Wins delegated to Module 4 Citation Authority which has
proper DR + typology enrichment):
  1. Content Gaps    — client pages to optimize (this module)
  2. Digital PR      — see peec_brain.citation_authority
  3. Competitor Wins — see peec_brain.citation_authority (future
     extension with brand-radar-cited-pages over time)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict, field
from typing import Optional


# ---------- Data models ----------


@dataclass
class PromptVisibility:
    """Per-prompt AI visibility from Peec (brand_report with prompt_id dimension)."""
    prompt_id: str
    prompt_text: str
    visibility: float              # 0.0 to 1.0
    mention_count: int
    chats_total: int
    topic_id: Optional[str] = None
    branded: str = "unknown"       # "branded" | "non_branded" | "unknown"
    top_competitors: list[str] = field(default_factory=list)  # §2ter names of top 3 competitors cited on this prompt


@dataclass
class ClientPage:
    """A high-traffic client page from Ahrefs site-explorer-top-pages."""
    url: str
    sum_traffic: int
    top_keyword: str
    top_keyword_volume: int = 0
    top_keyword_best_position: int = 0


@dataclass
class ContentGap:
    """One row of the content_gaps.csv output."""
    rank: int
    prompt_id: str
    prompt_text: str
    branded: str                     # §2ter
    visibility: float
    visibility_pct: str
    suggested_url: str
    page_type: str                   # §2ter: commercial | editorial | landing | other
    suggested_url_top_keyword: str
    suggested_url_traffic: int
    top3_competitors_occupying: str  # §2ter: pipe-separated list, ordered
    match_score: float
    priority_score: float
    suggested_action: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- Internals ----------


_WS = re.compile(r"\s+")
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "en", "et", "est",
    "à", "au", "aux", "pour", "dans", "sur", "avec", "par", "ce", "cette",
    "ces", "son", "sa", "ses", "quel", "quelle", "quels", "quelles",
    "comment", "pourquoi", "qui", "que", "qu", "c", "n", "y", "il", "elle",
    "mon", "ma", "mes", "meilleur", "meilleure", "meilleurs", "meilleures",
    "est-ce", "il", "peau", "produit", "produits",
    "the", "a", "an", "is", "are", "and", "or", "of", "in", "on", "for",
    "to", "what", "how", "why", "which", "when", "who", "best",
}


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _tokens(text: str) -> set[str]:
    t = _strip_accents(text).lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    return {w for w in _WS.split(t) if w and w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _decide_action(
    visibility: float,
    match_score: float,
    has_matching_page: bool,
) -> str:
    """Suggest an SEO action based on visibility + match quality."""
    if not has_matching_page:
        return "Créer une page dédiée (aucune page existante ne couvre ce prompt)"
    if visibility == 0.0:
        return "Optimiser pour l'AI visibility : FAQ, structure H2/H3 claire, citations externes"
    if visibility < 0.3:
        return "Renforcer le contenu : ajouter des sections spécifiques au prompt, autorités citées"
    if visibility < 0.5:
        return "Ajustements de structure : listes, citations, data points explicites"
    return "Monitoring — page déjà citée, pas d'action urgente"


# §2ter — URL-based page-type classification.
# Returns one of: "commercial" | "editorial" | "landing" | "other".
_COMMERCIAL_PATTERNS = [
    r"/produit/", r"/product/", r"/shop/", r"/achat/", r"/acheter",
    r"/[A-Z0-9]{3,}-LAC\.html",                     # Lancôme SKU pages
    r"/[0-9]+-[A-Z]+\.html$",                        # generic SKU
    r"\.html$",                                      # Lancôme flat product pages
    r"/catalog/", r"/boutique/",
]
_EDITORIAL_PATTERNS = [
    r"/blog/", r"/article/", r"/beauty-magazine/", r"/magazine/",
    r"/conseils?/", r"/guide/", r"/tutoriel/", r"/actu/",
    r"/news/", r"/mag/", r"/editorial/",
    r"/comment-", r"/pourquoi-", r"/quel-",
    r"/routine-", r"/astuces?/",
]
_LANDING_PATTERNS = [
    r"/soin/par-categorie/[^/]+/?$",                 # category pages
    r"/maquillage/[^/]+/?$",
    r"/parfum/[^/]+/?$",
    r"/par-gamme/[^/]+/?$",
]


def classify_page_type(url: str, title: str = "") -> str:
    """Simple URL-based page-type classification (§2ter)."""
    import re as _re
    u = url.lower()
    path = u.split("?", 1)[0].split("#", 1)[0]

    # Root / homepage
    if path.rstrip("/") == "" or path.count("/") <= 3 and not _re.search(r"\.html$|/[a-z]{2}\-[a-z]{2}/", path):
        # Very shallow URL → likely category / landing
        if _re.search(r"/$", path):
            return "landing"

    for pat in _EDITORIAL_PATTERNS:
        if _re.search(pat, path):
            return "editorial"
    for pat in _COMMERCIAL_PATTERNS:
        if _re.search(pat, path):
            return "commercial"
    for pat in _LANDING_PATTERNS:
        if _re.search(pat, path):
            return "landing"

    return "other"


# ---------- Public API ----------


def build_content_gaps(
    prompt_visibilities: list[PromptVisibility],
    client_pages: list[ClientPage],
    *,
    max_results: int = 30,
    visibility_threshold: float = 0.5,
    match_threshold: float = 0.10,
    include_branded: bool = False,     # §2ter default: non-branded only
) -> list[ContentGap]:
    """Build the Content Gaps list.

    For each prompt below visibility_threshold, find the client page whose
    top_keyword best matches the prompt text (via Jaccard token overlap).
    Priority is traffic × (1 - visibility), filtering matches below
    match_threshold.

    §2ter:
      - Default filters out `branded` prompts (their visibility is
        structurally high). Flip include_branded=True to include them.
      - Each ContentGap carries `top3_competitors_occupying` and
        `page_type` enrichments.

    Args:
      prompt_visibilities : per-prompt visibility (Peec brand_report) —
                            each PromptVisibility may include top_competitors
      client_pages        : top pages of client (Ahrefs site-explorer-top-pages)
      visibility_threshold: skip prompts with visibility >= this value
      match_threshold     : drop candidates with jaccard(prompt, page) < this
      include_branded     : if False, skip prompts with branded="branded"

    Returns:
      List[ContentGap] sorted by priority_score desc, truncated to max_results.
    """
    # Index pages by keyword token set for fast matching
    pages_idx: list[tuple[ClientPage, set]] = [
        (p, _tokens(p.top_keyword)) for p in client_pages
    ]

    gaps: list[ContentGap] = []

    for pv in prompt_visibilities:
        if pv.visibility >= visibility_threshold:
            continue
        # §2ter: skip branded by default
        if not include_branded and pv.branded == "branded":
            continue

        prompt_tokens = _tokens(pv.prompt_text)
        if not prompt_tokens:
            continue

        # Find best-matching client page
        best_page = None
        best_tokens = set()
        best_score = 0.0
        for page, page_tokens in pages_idx:
            score = _jaccard(prompt_tokens, page_tokens)
            if score > best_score:
                best_score = score
                best_page = page
                best_tokens = page_tokens

        has_match = best_page is not None and best_score >= match_threshold
        action = _decide_action(pv.visibility, best_score, has_match)
        top3_str = " | ".join(pv.top_competitors[:3])

        if not has_match:
            gaps.append(
                ContentGap(
                    rank=0,  # filled below
                    prompt_id=pv.prompt_id,
                    prompt_text=pv.prompt_text,
                    branded=pv.branded,
                    visibility=pv.visibility,
                    visibility_pct=f"{pv.visibility * 100:.0f}%",
                    suggested_url="(à créer)",
                    page_type="other",
                    suggested_url_top_keyword="",
                    suggested_url_traffic=0,
                    top3_competitors_occupying=top3_str,
                    match_score=0.0,
                    priority_score=round((1 - pv.visibility) * 500, 1),
                    suggested_action=action,
                )
            )
            continue

        priority = best_page.sum_traffic * (1 - pv.visibility)
        page_type = classify_page_type(best_page.url, best_page.top_keyword)

        gaps.append(
            ContentGap(
                rank=0,  # filled below
                prompt_id=pv.prompt_id,
                prompt_text=pv.prompt_text,
                branded=pv.branded,
                visibility=pv.visibility,
                visibility_pct=f"{pv.visibility * 100:.0f}%",
                suggested_url=best_page.url,
                page_type=page_type,
                suggested_url_top_keyword=best_page.top_keyword,
                suggested_url_traffic=best_page.sum_traffic,
                top3_competitors_occupying=top3_str,
                match_score=round(best_score, 3),
                priority_score=round(priority, 1),
                suggested_action=action,
            )
        )

    gaps.sort(key=lambda g: g.priority_score, reverse=True)
    gaps = gaps[:max_results]
    for i, g in enumerate(gaps, start=1):
        g.rank = i
    return gaps


def build_digital_pr_stub(*_, **__) -> list[dict]:
    """Stub. Full impl needs:
    - Peec get_domain_report → LLM-cited domains (with citation_count per domain)
    - Ahrefs site-explorer-referring-domains (client) → already-linking domains
    - Output: domains cited by LLMs with no backlink to client yet.
    """
    return []


def build_competitor_wins_stub(*_, **__) -> list[dict]:
    """Stub. Full impl needs:
    - Ahrefs brand-radar-cited-pages filtered by competitor brand_ids
    - Delta over last 30 days to detect pages GAINING citations
    """
    return []

"""Module 1 — Prompt Discovery (fusion GSC + Ahrefs + product catalog).

Positioning vs other challenge submissions:
  - alexgum1/gsc2peecai already ships the GSC → Peec axis with dual-
    threshold archiving + SISTRIX volumes. We do not compete on that.
  - Our differentiator is the fusion of THREE sources:
      1. GSC queries (when ownership available)
      2. Ahrefs site-explorer-organic-keywords (rank/traffic data that
         Alexander's tool doesn't have)
      3. A per-client product catalog (specific product names like
         "La Vie Est Belle Intense" → specific prompts nobody else
         can reach from query data alone)

Pipeline: normalise keywords, classify intent, match against
known_products, reformulate into natural questions, deduplicate against
existing Peec prompts, propose topics, batch via create_prompts.

The module is pure data processing — MCP calls happen upstream in
the Cowork session or orchestration layer.

Public entry point: discover(...) -> list[PromptCandidate]
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------- Data models ----------


@dataclass
class KeywordInput:
    """A keyword from either GSC or Ahrefs site-explorer."""
    keyword: str
    volume: int = 0
    traffic: int = 0              # Ahrefs sum_traffic OR GSC clicks
    impressions: int = 0          # GSC impressions (0 if Ahrefs-only)
    position: float = 0.0
    source: str = "unknown"       # "gsc" | "ahrefs"


@dataclass
class PromptCandidate:
    """A generated prompt proposal for Peec."""
    question: str
    source_keyword: str
    volume: int
    traffic: int
    intent: str                   # branded|comparison|commercial|transactional|informational
    branded: str                  # "branded" | "non_branded" (orthogonal to intent)
    topic_suggested: str
    topic_existing_id: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    priority_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- Internals ----------


_WS = re.compile(r"\s+")

# Minimal French + English stopwords for Jaccard dedup
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "en", "et", "est",
    "à", "au", "aux", "pour", "dans", "sur", "avec", "par", "ce", "cette",
    "ces", "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes",
    "quel", "quelle", "quels", "quelles", "comment", "pourquoi", "qui",
    "que", "qu", "c", "n", "y", "il", "elle", "ils", "elles", "on",
    "the", "a", "an", "is", "are", "and", "or", "of", "in", "on", "for",
    "to", "what", "how", "why", "which", "best",
}


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace. Keeps accents."""
    return _WS.sub(" ", text.lower().strip())


def _normalize_fold(text: str) -> str:
    """Normalize + strip accents for robust matching (lancome == lancôme)."""
    return _strip_accents(_normalize(text))


def classify_branded(
    query: str,
    brand_patterns: list[str],
    product_patterns: list[str] | None = None,
    subbrand_patterns: list[str] | None = None,
) -> str:
    """Classify a query as `branded` or `non_branded` (§2bis of the brief).

    Branded = contains brand name, sub-brand line, or a specific product
    name from the client catalog.
    Non-branded = none of the above. This is where AI visibility gaps
    are the most diagnostic (0-15% typical) — the priority push to Peec.

    Pattern matching is accent-insensitive and case-insensitive.
    """
    product_patterns = product_patterns or []
    subbrand_patterns = subbrand_patterns or []

    q = _normalize_fold(query)

    for p in brand_patterns:
        if p and _normalize_fold(p) in q:
            return "branded"
    for p in subbrand_patterns:
        if p and _normalize_fold(p) in q:
            return "branded"
    for p in product_patterns:
        if p and _normalize_fold(p) in q:
            return "branded"
    return "non_branded"


def classify_intent(keyword: str, brand_aliases: list[str]) -> str:
    """Rule-based intent classification."""
    k = _normalize_fold(keyword)

    # Branded = any brand alias substring match
    for alias in brand_aliases:
        if alias and _normalize_fold(alias) in k:
            return "branded"

    # Comparison: vs / versus / ou bien / comparatif
    if re.search(r"\b(vs|versus)\b|\bou bien\b|\bcomparatif\b", k):
        return "comparison"

    # Commercial investigation
    if re.search(
        r"\b(meilleur|meilleure|meilleurs|meilleures|top\s+\d+|top|classement|review|avis|recommand)",
        k,
    ):
        return "commercial"

    # Transactional
    if re.search(
        r"\b(acheter|prix|commander|commande|ou\s+trouver|où\s+trouver|code\s+promo|reduction|réduction|soldes|promo)",
        k,
    ):
        return "transactional"

    # Informational
    if re.search(
        r"\b(comment|pourquoi|qu'est-ce|qu'est\s+ce|c'est\s+quoi|definition|définition|différence|difference)",
        k,
    ):
        return "informational"

    # Fallback
    return "informational"


def _is_already_question(text: str) -> bool:
    t = text.strip().lower()
    if t.endswith("?"):
        return True
    # Starts with interrogative word
    starts = ("comment ", "pourquoi ", "qu'est-ce", "qu est ce", "quel ", "quelle ",
              "quels ", "quelles ", "est-ce ", "est ce ", "combien ", "ou ", "où ",
              "how ", "why ", "what ", "which ", "when ", "who ")
    return t.startswith(starts)


def _match_known_product(
    keyword: str, known_products: dict
) -> Optional[dict]:
    """Return the product dict if keyword matches one of known_products.

    known_products format:
      {"La Vie Est Belle": {"category": "parfum", "aliases": ["la vie est belle", "la vie est belle parfum"]}}
    Match is substring-based on aliases, accent/case insensitive.
    """
    k = _normalize_fold(keyword)
    for product_name, meta in known_products.items():
        for alias in meta.get("aliases", []):
            if _normalize_fold(alias) in k:
                return {"name": product_name, **meta}
    return None


def generate_question(
    kw: KeywordInput,
    intent: str,
    brand_display_name: str = "",
    known_products: Optional[dict] = None,
    year: int = 2026,
) -> str:
    """Reformulate a raw keyword into a natural LLM-style question.

    Handles:
      - already-question keywords (kept as-is with minor polish)
      - known product names (templated with category + brand)
      - generic intents (branded, comparison, commercial, transactional, info)
    """
    known_products = known_products or {}
    k = kw.keyword.strip()

    # 1. Already a natural question — just normalize capitalization & trailing ?
    if _is_already_question(k):
        result = k[0].upper() + k[1:]
        if not result.endswith("?"):
            result = result.rstrip(".") + " ?"
        return result

    # 2. Known product name — specialized template
    product = _match_known_product(k, known_products)
    if product:
        cat = product.get("category", "produit")
        pname = product["name"]
        brand_suffix = f" de {brand_display_name}" if brand_display_name else ""
        return f"Que vaut le {cat} {pname}{brand_suffix} en {year} ?"

    k_lower = k.lower()

    if intent == "branded":
        # "mascara lancome" → "Que vaut le mascara Lancôme en 2026 ?"
        text = k
        if brand_display_name:
            # Replace any case/accent variant of brand aliases with the canonical name
            for alias in set([brand_display_name] + list(known_products.keys())):
                text = re.sub(
                    rf"\b{re.escape(alias)}\b", alias, text, flags=re.IGNORECASE
                )
            # Also replace unaccented brand variants with the display version
            fold = _strip_accents(brand_display_name).lower()
            text = re.sub(
                rf"\b{re.escape(fold)}\b",
                brand_display_name,
                text,
                flags=re.IGNORECASE,
            )
        return f"Que vaut le {text} en {year} ?"

    if intent == "comparison":
        return f"{k[0].upper() + k[1:]} : lequel choisir en {year} ?"

    if intent == "commercial":
        if re.match(r"meilleur[es]?\b", k_lower):
            return f"Quel est le {k} en {year} ?"
        return f"Quel est le meilleur {k} en {year} ?"

    if intent == "transactional":
        return f"Où acheter le {k} au meilleur prix en {year} ?"

    # Informational default
    return f"Qu'est-ce qu'un bon {k} en {year} ?"


def _tokens(text: str) -> set[str]:
    t = _normalize(text)
    t = re.sub(r"[^\w\s]", " ", t)
    return {w for w in t.split() if w and w not in _STOPWORDS}


def find_duplicate(
    candidate_q: str, existing_prompts: list[str], threshold: float = 0.55
) -> Optional[str]:
    """Return the matched existing prompt if candidate is a near-duplicate.

    Uses Jaccard similarity on content tokens. Threshold tuned for short
    questions ~ 6-15 content tokens.
    """
    cand = _tokens(candidate_q)
    if not cand:
        return None
    best = None
    best_ratio = 0.0
    for ep in existing_prompts:
        ep_tokens = _tokens(ep)
        if not ep_tokens:
            continue
        inter = len(cand & ep_tokens)
        union = len(cand | ep_tokens)
        ratio = inter / union if union else 0.0
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best = ep
    return best


def suggest_topic(
    keyword: str,
    intent: str,
    existing_topics: list[dict],          # [{"id", "name"}]
    category_hints: dict[str, list[str]], # {topic_name: [hint_substrings]}
) -> tuple[str, Optional[str]]:
    """Return (topic_name, existing_topic_id_or_None)."""
    k = _normalize(keyword)

    # 1. Try existing topics by name match or hint match
    for t in existing_topics:
        name = t["name"]
        name_tokens = _tokens(name)
        # direct token overlap
        if name_tokens & _tokens(keyword):
            return (name, t["id"])

    # 2. Try category_hints (new topics proposed)
    for topic_name, hints in category_hints.items():
        for hint in hints:
            if hint.lower() in k:
                # If a topic with that name already exists, reuse it
                for t in existing_topics:
                    if _normalize(t["name"]) == _normalize(topic_name):
                        return (t["name"], t["id"])
                return (topic_name, None)

    return ("Autres", None)


# ---------- Public API ----------


INTENT_WEIGHT = {
    "commercial": 1.20,
    "comparison": 1.10,
    "transactional": 1.00,
    "informational": 0.90,
    "branded": 0.70,
}


def _dedupe_keywords(keywords: list[KeywordInput]) -> list[KeywordInput]:
    """Deduplicate source keywords on normalized form, keeping max traffic."""
    by_norm: dict[str, KeywordInput] = {}
    for kw in keywords:
        key = _normalize_fold(kw.keyword)
        existing = by_norm.get(key)
        if existing is None or kw.traffic > existing.traffic:
            by_norm[key] = kw
    return list(by_norm.values())


def _is_pure_brand(keyword: str, brand_aliases: list[str]) -> bool:
    """Keyword IS a brand alias (exact match, ignoring case/accents)."""
    k = _normalize_fold(keyword)
    return any(_normalize_fold(a) == k for a in brand_aliases)


def discover(
    existing_prompts: list[str],
    existing_topics: list[dict],
    keywords: list[KeywordInput],
    brand_aliases: list[str],
    category_hints: dict[str, list[str]],
    *,
    brand_display_name: str = "",
    known_products: Optional[dict] = None,
    brand_patterns: Optional[list[str]] = None,
    product_patterns: Optional[list[str]] = None,
    subbrand_patterns: Optional[list[str]] = None,
    max_prompts: int = 30,
    dedup_threshold: float = 0.55,
    year: int = 2026,
) -> list[PromptCandidate]:
    """Main Module 1 pipeline.

    Steps:
      1. Classify each keyword's intent.
      2. Generate a natural question.
      3. Assign a topic (existing reuse or new proposal).
      4. Check duplication against existing prompts.
      5. Score by traffic × intent weight.
      6. Drop duplicates, sort by score, take top max_prompts.

    Args:
      existing_prompts: list of current Peec prompt texts for the project.
      existing_topics:  list of {"id", "name"} for the project.
      keywords:         combined GSC + Ahrefs input.
      brand_aliases:    list of brand name aliases to flag branded intent.
      category_hints:   {new_topic_name: [hint_substrings]} for new topic
                        proposals (e.g. {"Parfums": ["parfum", "eau de"]}).

    Returns:
      List of PromptCandidate sorted by priority_score desc.
    """
    # Pre-filters: dedupe by normalized form, drop pure brand-name queries
    keywords = _dedupe_keywords(keywords)
    keywords = [kw for kw in keywords if not _is_pure_brand(kw.keyword, brand_aliases)]

    # Default branded/non-branded patterns
    _brand_pats = brand_patterns if brand_patterns is not None else list(brand_aliases)
    _product_pats = product_patterns or []
    _subbrand_pats = subbrand_patterns or []

    candidates: list[PromptCandidate] = []

    for kw in keywords:
        intent = classify_intent(kw.keyword, brand_aliases)
        branded = classify_branded(
            kw.keyword,
            brand_patterns=_brand_pats,
            product_patterns=_product_pats,
            subbrand_patterns=_subbrand_pats,
        )
        question = generate_question(
            kw, intent,
            brand_display_name=brand_display_name,
            known_products=known_products,
            year=year,
        )
        topic_name, topic_id = suggest_topic(
            kw.keyword, intent, existing_topics, category_hints
        )
        dup = find_duplicate(question, existing_prompts, threshold=dedup_threshold)

        score_base = kw.traffic or kw.volume or 1
        priority = score_base * INTENT_WEIGHT.get(intent, 1.0)

        candidates.append(
            PromptCandidate(
                question=question,
                source_keyword=kw.keyword,
                volume=kw.volume,
                traffic=kw.traffic,
                intent=intent,
                branded=branded,
                topic_suggested=topic_name,
                topic_existing_id=topic_id,
                is_duplicate=bool(dup),
                duplicate_of=dup,
                priority_score=round(priority, 1),
            )
        )

    # Keep duplicates visible in an audit CSV, but final output filters them
    non_dup = [c for c in candidates if not c.is_duplicate]
    non_dup.sort(key=lambda c: c.priority_score, reverse=True)

    # Collapse candidates that generated the SAME question text (e.g. several
    # keyword variants mapping to the same product). Keep the top-score one,
    # sum the traffic, merge source keywords for transparency.
    by_question: dict[str, PromptCandidate] = {}
    for c in non_dup:
        key = _normalize_fold(c.question)
        existing = by_question.get(key)
        if existing is None:
            by_question[key] = c
        else:
            existing.traffic += c.traffic
            existing.volume += c.volume
            existing.priority_score += c.priority_score
            # Mark merged source keywords for audit
            existing.source_keyword = f"{existing.source_keyword} + {c.source_keyword}"

    merged = list(by_question.values())
    merged.sort(key=lambda c: c.priority_score, reverse=True)
    return merged[:max_prompts]


def build_peec_payload(
    selected: list[PromptCandidate],
    new_topic_map: dict[str, str] | None = None,
    tag_id_map: dict[str, str] | None = None,
) -> dict:
    """Build the `create_prompts` payload from selected candidates.

    Each prompt is systematically tagged with `branded:<value>` (§2bis)
    and `topic:<name>` so Module 2 and Module 4 can filter efficiently.

    Args:
      new_topic_map : after calling `create_topics`, map proposed topic
                      names to their real Peec topic_id.
      tag_id_map    : {"branded:non_branded": "tg_abc...", "branded:branded": "tg_def..."}
                      Resolved before the call via list_tags or create_tags.
    """
    prompts_payload = []
    new_topic_map = new_topic_map or {}
    tag_id_map = tag_id_map or {}

    for c in selected:
        topic_id = c.topic_existing_id or new_topic_map.get(c.topic_suggested)
        tag_key = f"branded:{c.branded}"
        tag_ids = [tag_id_map[tag_key]] if tag_key in tag_id_map else []
        prompts_payload.append({
            "text": c.question,
            "topic_id": topic_id,
            "tag_ids": tag_ids,
        })

    return {"prompts": prompts_payload}

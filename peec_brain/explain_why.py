"""Module 4 — Explain Why (LEGACY — superseded by Module 3 Structural Audit).

Kept in the codebase for backward compatibility with earlier runs.
See `peec_brain.structural_audit` for the current implementation which
extends this with a schema.org (Layer B) audit in addition to the
editorial analysis originally implemented here.

For any new run, prefer:
    from peec_brain.structural_audit import structural_audit
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Optional


# ---------- Data models ----------


@dataclass
class LLMResponse:
    """One chat / answer from Peec — the assistant response text."""
    chat_id: str
    prompt_text: str
    assistant_content: str
    brands_mentioned: list[str]    # names in citation order
    model_id: str                  # chatgpt-scraper, gemini, etc.


@dataclass
class PageAnalysis:
    """Structural analysis of a client page."""
    url: str
    title: str
    url_classification: str        # HOMEPAGE | CATEGORY_PAGE | COMPARISON | ...
    content_length: int
    content_truncated: bool
    substantive_tokens: set[str]   # deduped content tokens (accent-folded)
    h2_count: int
    bullet_count: int
    paragraph_count: int


@dataclass
class ExpectedTopic:
    """One LLM-expected topic, extracted from chat responses."""
    name: str                      # e.g. "Retinol"
    variants: list[str]            # alternate spellings
    frequency: int                 # how many chats mentioned it
    example_products: list[str]    # products cited alongside


@dataclass
class ContentBrief:
    """Output: a structured brief for the content team."""
    prompt_text: str
    page_url: str
    page_classification: str
    current_visibility_pct: str
    expected_topics_count: int
    covered_topics_count: int
    coverage_ratio: float
    missing_topics: list[str]
    citation_competitors: list[str]
    recommended_h2s: list[str]
    diagnosis: str
    action_items: list[str]

    def to_markdown(self) -> str:
        lines = [
            "# Content Brief — AI Visibility (legacy)",
            "",
            f"**Prompt**: {self.prompt_text}",
            f"**Target page**: {self.page_url}",
            f"**Current visibility**: {self.current_visibility_pct}",
            f"**Coverage**: {self.covered_topics_count}/{self.expected_topics_count} LLM-expected topics ({self.coverage_ratio:.0%})",
            "",
            "## Diagnosis",
            "",
            self.diagnosis,
            "",
            "## Missing topics (what LLMs expect, your page lacks)",
            "",
        ]
        if self.missing_topics:
            for t in self.missing_topics:
                lines.append(f"- {t}")
        else:
            lines.append("- (none — full topical coverage achieved)")

        lines.extend([
            "",
            "## Competitors cited on this query",
            "",
        ])
        if self.citation_competitors:
            for c in self.citation_competitors:
                lines.append(f"- {c}")
        else:
            lines.append("- (no competitors cited in the analyzed chats)")

        lines.extend([
            "",
            "## Recommended H2 sections to add",
            "",
        ])
        for h2 in self.recommended_h2s:
            lines.append(f"### {h2}")
            lines.append("")

        lines.extend([
            "## Action items",
            "",
        ])
        for i, a in enumerate(self.action_items, start=1):
            lines.append(f"{i}. {a}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- Internals ----------


_WS = re.compile(r"\s+")
_HEADING_LINE_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.MULTILINE)
_BOLD_HEADING_RE = re.compile(r"\*\*([^*]+)\*\*")
_NUMBERING_PREFIX_RE = re.compile(r"^(?:\d+[\.\)]\s*)+")
_BOLD_WRAPPER_RE = re.compile(r"^\*+\s*|\s*\*+$")
_META_TOPIC_FILTERS = {
    "trends to watch", "trends",
    "popular examples", "examples",
    "conclusion", "to sum up", "summary",
    "note", "notes", "takeaways",
    "disclaimer", "warning", "good to know",
    # French fallbacks
    "tendances à suivre", "tendances", "exemples populaires",
    "exemples", "en résumé", "à retenir", "pour conclure",
    "avertissement", "attention", "bon à savoir",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _fold(s: str) -> str:
    return _strip_accents(s).lower().strip()


def _tokens(text: str) -> set[str]:
    t = _strip_accents(text).lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return {w for w in _WS.split(t) if w and len(w) > 2}


def _clean_heading(raw: str) -> str:
    """Strip numbering, bold wrappers, parenthetical clarifications."""
    s = raw.strip()
    s = _NUMBERING_PREFIX_RE.sub("", s)
    s = _BOLD_WRAPPER_RE.sub("", s).strip()
    s = _BOLD_WRAPPER_RE.sub("", s).strip()
    s = s.rstrip(":").strip()
    s = re.sub(r"\s*\([^)]+\)\s*$", "", s).strip()
    return s


def extract_expected_topics(responses: list[LLMResponse]) -> list[ExpectedTopic]:
    """Extract high-level topics the LLM expects (H2-level patterns)."""
    topic_counts: dict[str, dict] = {}

    for resp in responses:
        content = resp.assistant_content
        brand_keys = {_fold(b) for b in resp.brands_mentioned}

        # Pattern 1: markdown headings (##, ###, ####)
        for m in _HEADING_LINE_RE.finditer(content):
            headline = _clean_heading(m.group(2))
            if not headline or not (3 <= len(headline) <= 60):
                continue
            key = _fold(headline)
            if key in _META_TOPIC_FILTERS or any(f in key for f in _META_TOPIC_FILTERS):
                continue
            if key in brand_keys:
                continue
            topic_counts.setdefault(key, {
                "name": headline,
                "variants": set(),
                "frequency": 0,
                "example_products": set(),
            })
            topic_counts[key]["frequency"] += 1
            topic_counts[key]["variants"].add(headline)

        # Pattern 2: bold section leaders (weaker signal)
        for m in _BOLD_HEADING_RE.finditer(content):
            headline = _clean_heading(m.group(1))
            if not headline or not (3 <= len(headline) <= 60):
                continue
            key = _fold(headline)
            if key in brand_keys:
                continue
            if key in _META_TOPIC_FILTERS or any(f in key for f in _META_TOPIC_FILTERS):
                continue
            if any(bk in key for bk in brand_keys):
                continue
            topic_counts.setdefault(key, {
                "name": headline,
                "variants": set(),
                "frequency": 0,
                "example_products": set(),
            })
            topic_counts[key]["frequency"] += 0.5
            topic_counts[key]["variants"].add(headline)

    topics: list[ExpectedTopic] = []
    for key, data in topic_counts.items():
        if data["frequency"] < 1:
            continue
        topics.append(ExpectedTopic(
            name=data["name"],
            variants=sorted(data["variants"]),
            frequency=int(data["frequency"] * 2) // 2,
            example_products=[],
        ))

    topics.sort(key=lambda t: t.frequency, reverse=True)
    return topics


def analyze_page(
    url: str,
    title: str,
    url_classification: str,
    content: str,
    content_length: int = 0,
    truncated: bool = False,
) -> PageAnalysis:
    """Structural analysis of a client page content."""
    h2_count = len(_HEADING_LINE_RE.findall(content))
    bullet_count = sum(1 for line in content.splitlines() if line.lstrip().startswith(("-", "*", "•")))
    paragraph_count = sum(1 for p in content.split("\n\n") if len(p.strip()) > 80)
    return PageAnalysis(
        url=url,
        title=title,
        url_classification=url_classification,
        content_length=content_length or len(content),
        content_truncated=truncated,
        substantive_tokens=_tokens(content),
        h2_count=h2_count,
        bullet_count=bullet_count,
        paragraph_count=paragraph_count,
    )


def build_content_brief(
    prompt_text: str,
    current_visibility: float,
    expected_topics: list[ExpectedTopic],
    page: PageAnalysis,
    citation_competitors: list[str],
) -> ContentBrief:
    """Compare page against expected topics → brief."""
    missing: list[str] = []
    covered = 0

    for t in expected_topics:
        found = False
        t_tokens = _tokens(t.name)
        if t_tokens and len(t_tokens & page.substantive_tokens) >= max(1, int(len(t_tokens) * 0.6)):
            found = True
        if not found:
            for v in t.variants:
                if _fold(v) in _fold(" ".join(page.substantive_tokens)):
                    found = True
                    break
        if found:
            covered += 1
        else:
            missing.append(t.name)

    coverage = covered / max(1, len(expected_topics))

    diagnosis = _diagnose(page, coverage, current_visibility)
    recommended_h2s = [_to_h2(m) for m in missing]
    action_items = _build_action_items(page, coverage, missing, citation_competitors)

    return ContentBrief(
        prompt_text=prompt_text,
        page_url=page.url,
        page_classification=page.url_classification,
        current_visibility_pct=f"{current_visibility * 100:.0f}%",
        expected_topics_count=len(expected_topics),
        covered_topics_count=covered,
        coverage_ratio=round(coverage, 3),
        missing_topics=missing,
        citation_competitors=citation_competitors,
        recommended_h2s=recommended_h2s,
        diagnosis=diagnosis,
        action_items=action_items,
    )


def _diagnose(page: PageAnalysis, coverage: float, visibility: float) -> str:
    bits = []
    if page.url_classification == "CATEGORY_PAGE" and page.paragraph_count < 3:
        bits.append(
            "The target page is a category page with almost no substantive content "
            f"(~{page.paragraph_count} paragraphs, {page.h2_count} H2s). LLMs find "
            "nothing to cite — they prefer 'explainer' pages with ingredients, "
            "comparisons, evidence and specific product picks."
        )
    elif page.h2_count < 3:
        bits.append(
            f"The page has only {page.h2_count} H2s — LLMs favour structured pages "
            "with 5-10+ clear sections."
        )

    if coverage < 0.3:
        bits.append(
            f"Very low topical coverage ({coverage:.0%}): the page does not cover "
            "the topics LLMs expect on this query."
        )
    elif coverage < 0.6:
        bits.append(
            f"Partial coverage ({coverage:.0%}): the page touches some expected "
            "topics but misses several."
        )

    if visibility == 0:
        bits.append("Zero brand mentions detected in the analysed chats.")

    if not bits:
        bits.append("Structurally comparable page — investigate other signals (authority, freshness).")
    return " ".join(bits)


def _to_h2(topic: str) -> str:
    cleaned = re.sub(r"^[\d\.\-\*\s]+", "", topic).strip()
    return cleaned[0].upper() + cleaned[1:] if cleaned else topic


def _build_action_items(
    page: PageAnalysis, coverage: float, missing: list[str], competitors: list[str]
) -> list[str]:
    items = []
    if page.url_classification == "CATEGORY_PAGE" and page.paragraph_count < 5:
        items.append(
            "Create an editorial block at the top of the category page (300-500 "
            "words) covering the sub-topics above with dedicated H2s."
        )
    if missing:
        items.append(
            f"Add sections for the {len(missing)} missing topics identified "
            "(see 'Recommended H2 sections')."
        )
    if competitors:
        items.append(
            "Study the structure of the competitor pages the LLMs cite "
            f"({', '.join(competitors[:3])}): content depth, external citations, "
            "H2/H3 structure."
        )
    items.append(
        "Cite 2-3 external authorities (studies, dermatologists, specialist "
        "press) inside the copy — LLMs favour sources that themselves cite."
    )
    items.append(
        "Name active ingredients and their benefits explicitly in the first "
        "paragraphs — not only inside product tiles."
    )
    return items

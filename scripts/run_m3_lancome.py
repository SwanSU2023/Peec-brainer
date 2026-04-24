"""Demo — Module 3 Structural Audit on the sérum anti-âge prompt.

Pipeline:
  1. Load the Lancôme brand target page content (from Peec get_url_content fixture).
  2. Load 3 LLM-cited pages content (vogue.fr, healthline.com, vogue.co.uk).
  3. Layer A — editorial audit on all 4 pages (runs on markdown).
  4. Layer B — schema audit using representative sample HTML fixtures
     (since the sandbox blocks direct HTML fetch; run `fetch_and_audit.py`
     outside the sandbox for a live Layer B).
  5. Diff brand vs cited pages → prescriptive actions.
  6. Output markdown brief + JSON.

Usage:
  python3 scripts/run_m3_lancome.py
  python3 scripts/run_m3_lancome.py --editorial-only   # skip Layer B samples
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from peec_brain.structural_audit import (
    audit_page,
    structural_audit,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
CITED_DIR = FIXTURES / "lancome_cited_pages_content"
SAMPLE_HTML = FIXTURES / "sample_html"
OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAND_PAGE_FIXTURE = FIXTURES / "lancome_url_content_serum_visage.json"
CITED_PAGE_META_FIXTURE = FIXTURES / "lancome_cited_pages_serum_antiage.json"

PROMPT_TEXT = "Quel est le meilleur sérum anti-âge en 2026 selon les dermatologues ?"


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main(editorial_only: bool = False) -> int:
    # 1. Brand page
    brand = _load_json(BRAND_PAGE_FIXTURE)
    brand_html_sample = _load_html(SAMPLE_HTML / "lancome_serum_visage.html") if not editorial_only else None
    brand_audit = audit_page(
        url=brand["url"],
        title=brand.get("title", ""),
        url_classification=brand.get("url_classification", "UNKNOWN"),
        content_markdown=brand.get("content", ""),
        raw_html=brand_html_sample,
        is_cited=False,
    )

    # 2. Cited pages — load meta + content fixtures
    meta = _load_json(CITED_PAGE_META_FIXTURE)
    meta_by_url = {p["url"]: p for p in meta["pages"]}

    cited_fixtures = [
        ("vogue_fr", SAMPLE_HTML / "vogue_serum.html"),
        ("healthline", SAMPLE_HTML / "healthline_serum.html"),
        ("vogue_uk", SAMPLE_HTML / "vogue_serum.html"),
    ]

    cited_audits = []
    for fixture_stem, html_path in cited_fixtures:
        data = _load_json(CITED_DIR / f"{fixture_stem}.json")
        m = meta_by_url.get(data["url"], {})
        raw_html = _load_html(html_path) if not editorial_only else None
        # healthline gets its own sample HTML, others share the vogue sample
        if fixture_stem == "healthline" and not editorial_only:
            raw_html = _load_html(SAMPLE_HTML / "healthline_serum.html")

        cited_audits.append(audit_page(
            url=data["url"],
            title=data.get("title", ""),
            url_classification=data.get("url_classification", "UNKNOWN"),
            content_markdown=data.get("content_excerpt_3000", ""),
            raw_html=raw_html,
            is_cited=True,
            citation_count=m.get("citation_count", 0),
            retrieval_count=m.get("retrieval_count", 0),
            citation_rate=m.get("citation_rate", 0.0),
        ))

    # 3. Diff
    diff = structural_audit(
        prompt_text=PROMPT_TEXT,
        brand_page=brand_audit,
        cited_pages=cited_audits,
    )

    # 4. Log + persist
    print(f"Lancôme — Module 3 Structural Audit")
    print(f"  Prompt     : {PROMPT_TEXT}")
    print(f"  Brand page : {brand_audit.url}")
    print(f"  Layer B    : {'ON (sample HTML)' if not editorial_only else 'OFF'}")
    print()
    print(f"Brand editorial : H2={brand_audit.editorial.h2_count} | "
          f"ingredients={len(brand_audit.editorial.ingredient_mentions)} | "
          f"experts={brand_audit.editorial.expert_quote_count} | "
          f"tables={brand_audit.editorial.comparison_table_count}")
    if not editorial_only:
        print(f"Brand schema    : types={brand_audit.schema.jsonld_types}")
    print()

    for a in cited_audits:
        print(f"Cited {a.url[:60]:60s} rate={a.citation_rate:.2f}")
        print(f"  editorial : H2={a.editorial.h2_count} | "
              f"ing={len(a.editorial.ingredient_mentions)} | "
              f"exp={a.editorial.expert_quote_count} | "
              f"tbl={a.editorial.comparison_table_count}")
        if not editorial_only:
            print(f"  schema    : types={a.schema.jsonld_types}")
    print()
    print(f"Editorial gaps   : {len(diff.editorial_gaps)}")
    print(f"Schema gaps      : {len(diff.schema_gaps)}")
    print(f"Actions          : {len(diff.prescriptive_actions)}")
    print()
    print("VERDICT :")
    print(f"  {diff.verdict}")
    print()

    md_path = OUT_DIR / "lancome_m3_structural_audit_serum.md"
    md_path.write_text(diff.to_markdown(), encoding="utf-8")
    print(f"Markdown saved : {md_path}")

    json_path = OUT_DIR / "lancome_m3_structural_audit_serum.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(diff.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"JSON saved     : {json_path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--editorial-only", action="store_true", help="Skip Layer B (schema) audit.")
    args = parser.parse_args()
    raise SystemExit(main(editorial_only=args.editorial_only))

"""Demo — run Module 2 (Gap Analyzer) Content Gaps on Lancome fixtures.

Includes §2ter enrichments:
  - Filter non-branded by default (branded prompts skipped).
  - Each row carries top3_competitors_occupying (from brands_mentioned
    aggregated over chats).
  - Each row carries page_type classification (commercial/editorial/
    landing/other) via URL regex.

Uses real data collected from Peec MCP + Ahrefs MCP on 2026-04-25.

Output: content_gaps.csv — Lancome pages to optimize for AI visibility,
prioritized by traffic × (1 - visibility).
"""

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from peec_brain.gap_analyzer import (
    PromptVisibility,
    ClientPage,
    build_content_gaps,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_prompt_id_to_text_map(fixtures_dir: Path) -> dict[str, str]:
    path = fixtures_dir / "lancome_prompt_id_to_text.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main(include_branded: bool = False) -> int:
    prompt_texts_by_id = _load_prompt_id_to_text_map(FIXTURES)

    with open(FIXTURES / "lancome_brand_report_prompts.json", encoding="utf-8") as f:
        br = json.load(f)
    with open(FIXTURES / "lancome_competitors_by_prompt.json", encoding="utf-8") as f:
        comps = json.load(f)["by_prompt"]
    with open(FIXTURES / "lancome_branded_by_prompt.json", encoding="utf-8") as f:
        branded_map = json.load(f)["by_prompt"]

    visibilities = []
    for row in br["per_prompt"]:
        pid = row["prompt_id"]
        text = prompt_texts_by_id.get(pid, "(prompt text not found)")
        visibilities.append(PromptVisibility(
            prompt_id=pid,
            prompt_text=text,
            visibility=row["visibility"],
            mention_count=row["mention_count"],
            chats_total=row["chats_total"],
            branded=branded_map.get(pid, "unknown"),
            top_competitors=comps.get(pid, []),
        ))

    with open(FIXTURES / "lancome_top_pages.json", encoding="utf-8") as f:
        pages_raw = json.load(f)
    pages = [
        ClientPage(
            url=p["url"],
            sum_traffic=p.get("sum_traffic", 0),
            top_keyword=p.get("top_keyword", ""),
            top_keyword_volume=p.get("top_keyword_volume", 0),
            top_keyword_best_position=p.get("top_keyword_best_position", 0),
        )
        for p in pages_raw
    ]

    gaps = build_content_gaps(
        prompt_visibilities=visibilities,
        client_pages=pages,
        max_results=20,
        visibility_threshold=0.5,
        match_threshold=0.10,
        include_branded=include_branded,
    )

    # Stats
    total_low = sum(1 for v in visibilities if v.visibility < 0.5)
    total_nb = sum(1 for v in visibilities if v.visibility < 0.5 and v.branded == "non_branded")
    by_type: dict[str, int] = {}
    for g in gaps:
        by_type[g.page_type] = by_type.get(g.page_type, 0) + 1

    print(f"Lancome — Module 2 Content Gaps (§2ter enriched)")
    print(f"  Mode                         : {'ALL (include_branded=True)' if include_branded else 'NON-BRANDED (default)'}")
    print(f"  Prompts low-visibility total : {total_low}")
    print(f"  Prompts low-vis + non-branded: {total_nb}")
    print(f"  Top pages available          : {len(pages)}")
    print(f"  Content gaps identified      : {len(gaps)}")
    print(f"  By page type                 : {by_type}")
    print()
    print(f"Top 10 pages to optimize (priority = traffic × (1 - visibility)) :")
    print("-" * 100)
    for g in gaps[:10]:
        print(f"  #{g.rank:<2} [{g.visibility_pct:>3}] priority {g.priority_score:>9.0f}  [{g.page_type:>10}]")
        print(f"     prompt : {g.prompt_text[:90]}")
        print(f"     page   : {g.suggested_url}")
        print(f"     comp   : {g.top3_competitors_occupying}")
        print(f"     action : {g.suggested_action}")
        print()

    # §2ter output CSV (new format with rank, page_type, competitors)
    csv_path = OUT_DIR / "lancome_content_gaps.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "rank", "url", "type", "traffic_month", "visibility_pct",
                "prompt_id", "prompt_text", "branded",
                "top3_competitors_occupying", "priority_score",
                "suggested_action",
            ],
        )
        w.writeheader()
        for g in gaps:
            w.writerow({
                "rank": g.rank,
                "url": g.suggested_url,
                "type": g.page_type,
                "traffic_month": g.suggested_url_traffic,
                "visibility_pct": g.visibility_pct,
                "prompt_id": g.prompt_id,
                "prompt_text": g.prompt_text,
                "branded": g.branded,
                "top3_competitors_occupying": g.top3_competitors_occupying,
                "priority_score": g.priority_score,
                "suggested_action": g.suggested_action,
            })
    print(f"CSV saved: {csv_path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-branded", action="store_true", help="Include branded prompts in the gap analysis.")
    args = parser.parse_args()
    raise SystemExit(main(include_branded=args.include_branded))

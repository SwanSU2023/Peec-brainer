"""Demo — run Module 1 (Prompt Discovery) on Lancome fixtures.

Includes §2bis branded/non-branded overlay: non-branded prompts are
pushed to Peec by default; branded prompts go to a backlog CSV and can
be pushed with --include-branded.

This is a dry-run: no prompts are created in Peec.
"""

import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from peec_brain.discovery import (
    KeywordInput,
    discover,
    build_peec_payload,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _export_csv(candidates, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "question", "source_keyword", "volume", "traffic",
                "intent", "branded", "topic_suggested", "topic_existing_id",
                "is_duplicate", "duplicate_of", "priority_score",
            ],
        )
        w.writeheader()
        for c in candidates:
            w.writerow(c.to_dict())


def main() -> int:
    with open(FIXTURES / "lancome_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(FIXTURES / "lancome_existing_prompts.json", encoding="utf-8") as f:
        existing = json.load(f)
    with open(FIXTURES / "lancome_keywords_combined.json", encoding="utf-8") as f:
        raw_kws = json.load(f)

    keywords = [
        KeywordInput(
            keyword=k["keyword"],
            volume=int(k.get("volume") or 0),
            traffic=int(k.get("traffic") or 0),
            impressions=int(k.get("impressions") or 0),
            source=k.get("source", "unknown"),
        )
        for k in raw_kws
    ]

    candidates = discover(
        existing_prompts=existing,
        existing_topics=cfg["existing_topics"],
        keywords=keywords,
        brand_aliases=cfg["brand_aliases"],
        category_hints=cfg["category_hints"],
        brand_display_name=cfg.get("brand_display_name", ""),
        known_products=cfg.get("known_products", {}),
        brand_patterns=cfg.get("brand_patterns"),
        product_patterns=cfg.get("product_patterns"),
        subbrand_patterns=cfg.get("subbrand_patterns"),
        max_prompts=30,
        dedup_threshold=0.55,
        year=2026,
    )

    # Split branded vs non-branded (§2bis)
    non_branded = [c for c in candidates if c.branded == "non_branded"]
    branded = [c for c in candidates if c.branded == "branded"]

    # Stats
    by_topic_nb: dict[str, int] = {}
    for c in non_branded:
        by_topic_nb[c.topic_suggested] = by_topic_nb.get(c.topic_suggested, 0) + 1
    by_topic_br: dict[str, int] = {}
    for c in branded:
        by_topic_br[c.topic_suggested] = by_topic_br.get(c.topic_suggested, 0) + 1

    print(f"Module 1 — Lancôme — Run {__import__('datetime').date.today().isoformat()}")
    print(f"├── {len(candidates)} prompts générés au total")
    print(f"├── {len(branded)} branded (backlog, push via --include-branded)")
    for c in branded[:8]:
        print(f"│   - \"{c.question}\"")
    if len(branded) > 8:
        print(f"│   ... (+{len(branded) - 8} more)")
    print(f"├── {len(non_branded)} non-branded (à pousser en priorité)")
    for c in non_branded[:8]:
        print(f"│   - \"{c.question}\"")
    if len(non_branded) > 8:
        print(f"│   ... (+{len(non_branded) - 8} more)")
    topics_needed = sorted({c.topic_suggested for c in candidates if not c.topic_existing_id})
    print(f"└── {len(topics_needed)} topics à créer : {', '.join(topics_needed)}")
    print()
    print(f"By topic (non-branded): {by_topic_nb}")
    print(f"By topic (branded    ): {by_topic_br}")
    print()

    # Export 2 CSVs
    nb_path = OUT_DIR / "lancome_m1_non_branded.csv"
    br_path = OUT_DIR / "lancome_m1_branded_backlog.csv"
    _export_csv(non_branded, nb_path)
    _export_csv(branded, br_path)
    print(f"CSV non-branded (push par défaut) : {nb_path}")
    print(f"CSV branded (backlog)             : {br_path}")

    # Legacy single CSV for backward compatibility with the dashboard
    _export_csv(candidates, OUT_DIR / "lancome_m1_dry_run.csv")

    # Show the Peec payload (non-branded first, with tags)
    # Placeholder tag IDs — will be replaced with real tg_... after list_tags.
    tag_id_map = {
        "branded:non_branded": "tg_PLACEHOLDER_NON_BRANDED",
        "branded:branded":     "tg_PLACEHOLDER_BRANDED",
    }
    print()
    print(f"Sample Peec `create_prompts` payload (top 3 non-branded):")
    payload = build_peec_payload(non_branded[:3], tag_id_map=tag_id_map)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

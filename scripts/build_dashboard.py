"""Build the Peec Brain dashboard HTML by injecting M1/M2/M4 outputs
from fixtures into the index.html template.

Output: repo/dashboard/dist/index.html (self-contained, openable locally).
"""

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "dashboard" / "index.html"
OUT = ROOT / "dashboard" / "dist" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUTS = ROOT / "outputs"


def _csv_to_list(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _coerce_numbers(row: dict, fields: list[str]) -> dict:
    for f in fields:
        if f in row and row[f] != "":
            try:
                row[f] = float(row[f]) if "." in str(row[f]) else int(row[f])
            except ValueError:
                pass
    return row


def main() -> int:
    # M1
    m1_rows = _csv_to_list(OUTPUTS / "lancome_m1_dry_run.csv")
    for r in m1_rows:
        _coerce_numbers(r, ["volume", "traffic", "priority_score"])
        r["is_duplicate"] = r.get("is_duplicate", "False") == "True"

    # M2
    m2_rows = _csv_to_list(OUTPUTS / "lancome_content_gaps.csv")
    for r in m2_rows:
        _coerce_numbers(
            r,
            [
                "visibility", "suggested_url_traffic", "match_score",
                "priority_score",
            ],
        )

    # M4
    m4_data = json.loads((OUTPUTS / "lancome_m4_content_brief_serum.json").read_text(encoding="utf-8"))

    # Load template
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("{{ M1_JSON }}", json.dumps(m1_rows, ensure_ascii=False))
    html = html.replace("{{ M2_JSON }}", json.dumps(m2_rows, ensure_ascii=False))
    html = html.replace("{{ M4_JSON }}", json.dumps(m4_data, ensure_ascii=False))

    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard built : {OUT}")
    print(f"  M1 rows : {len(m1_rows)}")
    print(f"  M2 rows : {len(m2_rows)}")
    print(f"  M4 data : {m4_data.get('page_url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Standalone fetch + schema audit for Module 3 Layer B.

Run this script outside network-restricted environments (e.g. your Mac
terminal, a CI runner) to fetch raw HTML from cited URLs and extract
schema.org types via extruct. Output feeds directly into the full
Module 3 diff.

Why a separate script: Cowork sandboxes block outbound HTTP to non-
allowlisted domains, and Peec's `get_url_content` returns cleaned
markdown without preserving JSON-LD. This script bridges the gap.

Install:
    pip install extruct requests

Usage:
    python3 scripts/fetch_and_audit.py \\
        --urls https://healthline.com/... https://vogue.fr/... \\
        --out fixtures/live_schema_audit.json

    # Then re-run Module 3 in 'live mode':
    python3 scripts/run_m3_lancome.py --schema-from fixtures/live_schema_audit.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    import requests
    import extruct
    from w3lib.html import get_base_url
except ImportError:
    print("Install dependencies first: pip install extruct requests")
    sys.exit(2)


DEFAULT_UA = "Mozilla/5.0 (compatible; PeecBrainAudit/0.1; +https://github.com/SwanSU2023/peec-brain)"


def fetch_html(url: str, timeout: int = 20) -> tuple[str, int]:
    r = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
    r.raise_for_status()
    return r.text, r.status_code


def audit(url: str) -> dict:
    try:
        html, status = fetch_html(url)
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e)}

    base = get_base_url(html, url)
    data = extruct.extract(
        html, base_url=base,
        syntaxes=["json-ld", "microdata", "rdfa", "opengraph"],
    )

    def _collect(container: list, key_candidates: list[str]) -> list[str]:
        out: list[str] = []
        def _walk(obj):
            if isinstance(obj, dict):
                for k in key_candidates:
                    v = obj.get(k)
                    if isinstance(v, str):
                        out.append(v)
                    elif isinstance(v, list):
                        out.extend([x for x in v if isinstance(x, str)])
                for vv in obj.values():
                    _walk(vv)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v)
        for it in container:
            _walk(it)
        return out

    jsonld_types = _collect(data.get("json-ld", []), ["@type"])
    microdata_types = [t.rsplit("/", 1)[-1] for t in _collect(data.get("microdata", []), ["type"])]
    rdfa_types = _collect(data.get("rdfa", []), ["@type"])

    return {
        "url": url,
        "ok": True,
        "http_status": status,
        "jsonld_types": sorted(set(jsonld_types)),
        "microdata_types": sorted(set(microdata_types)),
        "rdfa_types": sorted(set(rdfa_types)),
        "opengraph": bool(data.get("opengraph")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch URLs and audit schemas.")
    parser.add_argument("--urls", nargs="+", required=True, help="URLs to audit.")
    parser.add_argument("--out", type=Path, required=True, help="JSON output path.")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between fetches (seconds).")
    args = parser.parse_args()

    results = []
    for i, url in enumerate(args.urls, start=1):
        print(f"[{i}/{len(args.urls)}] {url}")
        results.append(audit(url))
        if i < len(args.urls):
            time.sleep(args.delay)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

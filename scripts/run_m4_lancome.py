"""Demo — Module 4 Citation Authority Audit on the sérum anti-âge prompt.

Pipeline:
  1. Load cited domains fixture (from Peec get_domain_report).
  2. Load domain_ratings fixture (from Ahrefs site-explorer-domain-rating).
  3. Load Lancôme brand refs + competitor list.
  4. Build GAP list = domains citing competitors but not Lancôme.
  5. Enrich with DR + typology + priority.
  6. Export CSV for the PR team.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from peec_brain.citation_authority import (
    CitedDomain,
    BrandRef,
    enrich_and_prioritize,
    export_csv,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


LANCOME_OWN_BRAND_ID = "kw_8781334e-24ab-47a0-91a9-df33b538345a"

# Top competitors tracked in the Lancôme Peec project (from list_brands + SOV ranking)
COMPETITORS = [
    BrandRef("kw_c401c82d-087c-411f-93b5-64463fee204d", "Estée Lauder"),
    BrandRef("kw_d8862fc3-0530-4e35-a05a-acfee1d5f6be", "Estee Lauder"),
    BrandRef("kw_0919414d-f975-4621-90cd-48734065b83e", "La Roche-Posay"),
    BrandRef("kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4", "The Ordinary"),
    BrandRef("kw_a59f091a-cc81-490c-9cd7-c1d97738dcaf", "Clarins"),
    BrandRef("kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e", "SkinCeuticals"),
    BrandRef("kw_c9e09aef-94ce-4a78-9f17-cf82a40ed6d5", "La Mer"),
    BrandRef("kw_757d406d-89fa-4245-a31a-960eddcb420f", "Sisley"),
    BrandRef("kw_3fc825ce-2663-4adc-96cb-0874e9bcf28b", "La Prairie"),
    BrandRef("kw_daa02882-744d-42b9-88f2-ce62f9c951ab", "Vichy"),
    BrandRef("kw_f9a68ee8-6c13-4a17-8755-8b949a1a5e5d", "Chanel"),
    BrandRef("kw_0be1278e-eb9c-4d0e-aa65-a96864891103", "CeraVe"),
    BrandRef("kw_312d0332-1d9f-4f82-aaea-49c86b542d59", "Dr Dennis Gross"),
    BrandRef("kw_a5eee504-0991-4546-8d9d-911fe58cee49", "Augustinus Bader"),
    BrandRef("kw_2b84b7c4-6fd3-4bbb-bb3a-0e7f38db0181", "Neutrogena"),
    BrandRef("kw_d47b4be8-71f3-4148-8635-b737a0381659", "Clinique"),
    BrandRef("kw_a8e1cff3-cba5-429c-b897-888dca55340a", "Caudalie"),
    BrandRef("kw_d6ac2cb5-4810-4df6-9c9b-f3a342c37262", "Avène"),
    BrandRef("kw_05fe9589-52ad-449a-81f1-f414270112d9", "L'Oréal Paris"),
    BrandRef("kw_0a1f0181-6b83-49ef-ab86-e8ea13103641", "L'Oreal"),
    BrandRef("kw_63f8546f-e560-4225-8913-fe0deb7c8253", "Sephora"),
    BrandRef("kw_1a31ca8c-d979-42c9-83fa-0ef84728ab14", "Olay"),
    BrandRef("kw_e59599cd-76c4-41d9-ad6e-065eba90485c", "Drunk Elephant"),
    BrandRef("kw_a438302d-6d8b-4c3f-9d12-974863fd6045", "Charlotte Tilbury"),
    BrandRef("kw_d3ae3e98-02f3-4fe5-916c-b95938c7d518", "Elemis"),
    BrandRef("kw_a00b1d98-b558-4fa9-a540-cf0551574350", "medik8"),
    BrandRef("kw_72388c81-7679-49d3-ba6e-95289df039f5", "Allies of Skin"),
    BrandRef("kw_12f6f4b2-7f3a-424d-9931-0a9624f4e1ee", "Paula's Choice"),
    BrandRef("kw_1f7a155b-e26a-4817-a5f7-556154ecafe1", "Pixi"),
    BrandRef("kw_02eb647c-fead-4279-8036-27f3d5f10f2b", "Sunday Riley"),
    BrandRef("kw_e7495569-c352-4bbe-8d64-6e0aaaf61c9d", "Glow Recipe"),
    BrandRef(LANCOME_OWN_BRAND_ID, "Lancôme", is_own=True),
]


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    domains_raw = _load_json(FIXTURES / "lancome_cited_domains_serum_antiage.json")
    ratings_raw = _load_json(FIXTURES / "lancome_domain_ratings.json")

    # Peec data — the brand_ids aren't in our fixture directly, they come from
    # the original get_domain_report call. We reconstruct from the raw response.
    # For demo: reuse the brand_ids seen in the get_domain_report earlier captured.
    # Because the fixture was trimmed, we hardcode the known brand_id lists here:
    domain_brand_ids = {
        "ma-sante.news": [],
        "vogue.fr": [
            "kw_757d406d-89fa-4245-a31a-960eddcb420f",  # Sisley
            "kw_8781334e-24ab-47a0-91a9-df33b538345a",  # Lancôme (own)
            "kw_a59f091a-cc81-490c-9cd7-c1d97738dcaf",  # Clarins
            "kw_a5eee504-0991-4546-8d9d-911fe58cee49",  # Augustinus Bader
            "kw_c401c82d-087c-411f-93b5-64463fee204d",  # Estée Lauder
            "kw_d8862fc3-0530-4e35-a05a-acfee1d5f6be",  # Estee Lauder
            "kw_e123092d-b133-4cfd-8a29-6fbd8dccbb2c",  # Shiseido
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",  # The Ordinary
            "kw_fd23945c-548b-4829-85a6-a874c0d0d4a3",  # NUXE
        ],
        "vogue.co.uk": [
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",  # SkinCeuticals
            "kw_312d0332-1d9f-4f82-aaea-49c86b542d59",  # Dr Dennis Gross
            "kw_72388c81-7679-49d3-ba6e-95289df039f5",  # Allies of Skin
            "kw_a00b1d98-b558-4fa9-a540-cf0551574350",  # medik8
            "kw_d3ae3e98-02f3-4fe5-916c-b95938c7d518",  # Elemis
            "kw_f9a68ee8-6c13-4a17-8755-8b949a1a5e5d",  # Chanel
            "kw_c8ce5838-1024-4c20-9789-654aa4f8e415",  # Barbara Sturm
        ],
        "nymag.com": [
            "kw_02eb647c-fead-4279-8036-27f3d5f10f2b",  # Sunday Riley
            "kw_0919414d-f975-4621-90cd-48734065b83e",  # La Roche-Posay
            "kw_0a1f0181-6b83-49ef-ab86-e8ea13103641",  # L'Oreal
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",  # CeraVe
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",  # SkinCeuticals
            "kw_63f8546f-e560-4225-8913-fe0deb7c8253",  # Sephora
            "kw_a00b1d98-b558-4fa9-a540-cf0551574350",  # medik8
            "kw_c401c82d-087c-411f-93b5-64463fee204d",  # Estée Lauder
            "kw_daa02882-744d-42b9-88f2-ce62f9c951ab",  # Vichy
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",  # The Ordinary
            "kw_e7495569-c352-4bbe-8d64-6e0aaaf61c9d",  # Glow Recipe
        ],
        "today.com": [
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",
            "kw_a438302d-6d8b-4c3f-9d12-974863fd6045",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
            "kw_e59599cd-76c4-41d9-ad6e-065eba90485c",
            "kw_12f6f4b2-7f3a-424d-9931-0a9624f4e1ee",
            "kw_252dd221-2c16-4c65-91bc-409c751fefc6",
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",
            "kw_b2e8b872-174d-4fd3-b839-f7705473b8dd",
            "kw_e68eb42c-5eb0-47f2-bd77-02868d23ff14",
        ],
        "healthline.com": [
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",
            "kw_2b84b7c4-6fd3-4bbb-bb3a-0e7f38db0181",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
        ],
        "cosmopolitan.com": [
            "kw_2b84b7c4-6fd3-4bbb-bb3a-0e7f38db0181",
        ],
        "forbes.com": [
            "kw_02eb647c-fead-4279-8036-27f3d5f10f2b",
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_0aa8fb77-14f9-4b62-beae-e085600cbb88",
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",
            "kw_63f8546f-e560-4225-8913-fe0deb7c8253",
            "kw_312d0332-1d9f-4f82-aaea-49c86b542d59",
            "kw_a8e1cff3-cba5-429c-b897-888dca55340a",
            "kw_c401c82d-087c-411f-93b5-64463fee204d",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
        ],
        "prevention.com": [
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",
            "kw_1a31ca8c-d979-42c9-83fa-0ef84728ab14",
            "kw_2b84b7c4-6fd3-4bbb-bb3a-0e7f38db0181",
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",
            "kw_312d0332-1d9f-4f82-aaea-49c86b542d59",
            "kw_63f8546f-e560-4225-8913-fe0deb7c8253",
            "kw_a00b1d98-b558-4fa9-a540-cf0551574350",
            "kw_daa02882-744d-42b9-88f2-ce62f9c951ab",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
        ],
        "topsante.com": [
            "kw_0a1f0181-6b83-49ef-ab86-e8ea13103641",
            "kw_daa02882-744d-42b9-88f2-ce62f9c951ab",
        ],
        "glowupbyparis.com": [
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_0be1278e-eb9c-4d0e-aa65-a96864891103",
            "kw_8781334e-24ab-47a0-91a9-df33b538345a",  # Lancôme (own)
            "kw_a59f091a-cc81-490c-9cd7-c1d97738dcaf",
            "kw_a8e1cff3-cba5-429c-b897-888dca55340a",
            "kw_d47b4be8-71f3-4148-8635-b737a0381659",
            "kw_d6ac2cb5-4810-4df6-9c9b-f3a342c37262",
            "kw_daa02882-744d-42b9-88f2-ce62f9c951ab",
        ],
        "aufeminin.com": [
            "kw_2b84b7c4-6fd3-4bbb-bb3a-0e7f38db0181",
            "kw_daa02882-744d-42b9-88f2-ce62f9c951ab",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
            "kw_e59599cd-76c4-41d9-ad6e-065eba90485c",
        ],
        "vogue.com": [
            "kw_12f6f4b2-7f3a-424d-9931-0a9624f4e1ee",
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",
            "kw_312d0332-1d9f-4f82-aaea-49c86b542d59",
            "kw_a00b1d98-b558-4fa9-a540-cf0551574350",
            "kw_d3ae3e98-02f3-4fe5-916c-b95938c7d518",
            "kw_f9a68ee8-6c13-4a17-8755-8b949a1a5e5d",
            "kw_0919414d-f975-4621-90cd-48734065b83e",
            "kw_e1e22df2-2670-42fc-9482-6c3cc789ecf4",
        ],
        "glamourmagazine.co.uk": [
            "kw_252dd221-2c16-4c65-91bc-409c751fefc6",
            "kw_2bec24ee-7d89-4cfc-88ee-48db5b747d1e",
        ],
        "sakhiyaskinclinic.com": [],
    }

    cited_domains = []
    for d in domains_raw["domains"]:
        cited_domains.append(CitedDomain(
            domain=d["domain"],
            classification=d.get("classification", "OTHER"),
            citation_count=d.get("citation_count", 0),
            retrieval_count=d.get("retrieval_count", 0),
            citation_rate=d.get("citation_rate", 0.0),
            mentioned_brand_ids=domain_brand_ids.get(d["domain"], []),
        ))

    domain_ratings = {
        r["domain"]: {"domain_rating": r["domain_rating"], "ahrefs_rank": r["ahrefs_rank"]}
        for r in ratings_raw["ratings"]
    }

    enriched = enrich_and_prioritize(
        cited_domains,
        own_brand_id=LANCOME_OWN_BRAND_ID,
        competitors=COMPETITORS,
        domain_ratings=domain_ratings,
    )

    print(f"Lancôme — Module 4 Citation Authority Audit")
    print(f"  Prompt          : Quel est le meilleur sérum anti-âge en 2026 selon les dermatologues ?")
    print(f"  Cited domains   : {len(cited_domains)}")
    print(f"  Gap domains     : {len(enriched)}  (cite competitors but never Lancôme)")
    print()
    by_priority = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for e in enriched:
        by_priority[e.outreach_priority].append(e)
    for bucket, items in by_priority.items():
        print(f"  {bucket:6s}: {len(items)}")
    print()
    print("Top 8 outreach targets :")
    print("-" * 100)
    for e in enriched[:8]:
        dr_s = f"DR {e.domain_rating:.0f}" if e.domain_rating is not None else "DR n/a"
        print(f"  [{e.outreach_priority:6s}] score {e.priority_score:5.2f}  {e.domain:30s}  {e.typology:20s}  {dr_s}")
        print(f"           cites: {', '.join(e.cited_competitors[:5])}{' ...' if e.competitor_count > 5 else ''}")
        print(f"           action: {e.recommended_action[:95]}")
        print()

    out_csv = OUT_DIR / "lancome_citation_authority_serum.csv"
    export_csv(enriched, out_csv)
    print(f"CSV saved : {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

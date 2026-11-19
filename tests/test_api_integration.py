import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as flask_app
from src.engine import parse_storage_specs, parse_weight_kg


client = flask_app.app.test_client()


def test_homepage_and_validation():
    home = client.get("/")
    assert home.status_code == 200

    assert client.get("/api/search").status_code == 400
    assert client.get("/api/search?q=   ").status_code == 400
    assert client.get("/api/search?q=laptop&top=0").status_code == 400
    assert client.get("/api/search?q=laptop&top=-1").status_code == 400
    assert client.get("/api/search?q=laptop&top=abc").status_code == 400
    assert client.get("/api/search?q=laptop&top=101").status_code == 400


def test_impossible_query_returns_empty_200():
    resp = client.get("/api/search", query_string={"q": "gaming maksimal 5 juta", "top": 10})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 0
    assert data["results"] == []
    assert data["relaxed"] is False


def test_negation_macbook_and_price_equivalence():
    d_no_gaming = client.get("/api/search", query_string={"q": "bukan laptop gaming", "top": 10}).get_json()
    assert d_no_gaming["count"] > 0
    assert all(r["category"].lower() != "gaming" for r in d_no_gaming["results"])

    d_mac = client.get("/api/search", query_string={"q": "laptop macbook", "top": 30}).get_json()
    assert d_mac["count"] > 0
    assert all(r["brand"].lower() == "apple" and "macbook" in r["name"].lower() for r in d_mac["results"])

    d_plain = client.get("/api/search", query_string={"q": "laptop maksimal 8000000", "top": 10}).get_json()
    d_rp = client.get("/api/search", query_string={"q": "laptop maksimal Rp8.000.000", "top": 10}).get_json()
    assert d_plain["constraints"] == d_rp["constraints"]
    assert [r["id"] for r in d_plain["results"]] == [r["id"] for r in d_rp["results"]]


def test_zero_constraint_violations_on_dataset():
    checks = [
        ("coding ssd 512gb", lambda r: parse_storage_specs(r["storage"])["ssd_gb"] >= 512 and int(r["ram"].replace("GB", "")) >= 8),
        ("kuliah ringan di bawah 8 juta", lambda r: r["price_idr"] < 8_000_000),
        ("ThinkPad RAM 16 GB", lambda r: "thinkpad" in r["name"].lower() and int(r["ram"].replace("GB", "")) >= 16),
        ("berat maksimal 1,5 kg", lambda r: parse_weight_kg(r["weight"]) <= 1.5),
        ("laptop tanpa HDD maksimal 10 juta", lambda r: parse_storage_specs(r["storage"])["hdd_gb"] == 0 and r["price_idr"] <= 10_000_000),
    ]
    for q, pred in checks:
        data = client.get("/api/search", query_string={"q": q, "top": 30}).get_json()
        assert data["count"] > 0, f"Harusnya ada hasil untuk: {q}"
        for r in data["results"]:
            assert pred(r), f"Pelanggaran constraint pada {q}: {r}"


def test_stats_endpoint_and_catalog_size():
    stats_resp = client.get("/api/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.get_json()
    assert stats["total_documents"] > 0
    assert stats["price_note"]

    search_resp = client.get("/api/search", query_string={"q": "thinkpad", "top": 5})
    assert search_resp.status_code == 200
    search_data = search_resp.get_json()
    assert search_data["catalog_size"] == stats["total_documents"]


def _extract_inches(display_str: str) -> float:
    import re
    m = re.search(r'(\d+(?:\.\d+)?)', str(display_str))
    return float(m.group(1)) if m else float('nan')


def _all_items_with_variants(row):
    return [row] + list(row.get("variants") or [])


def test_paket1_audit_price_component_and_conversational_queries():
    cases = [
        ("laptop harga maksimal 8 juta", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("maksimal 8 juta dong", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("maksimal Rp8 juta", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("budget Rp 8 juta", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("budget saya 8 juta", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("maksimal 8.000.000", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("≤ 8 juta", 125, lambda item: item["price_idr"] <= 8_000_000),
        ("minimal 5 juta dan maksimal 8 juta", 92, lambda item: 5_000_000 <= item["price_idr"] <= 8_000_000),
        ("antara 5 dan 8 juta", 92, lambda item: 5_000_000 <= item["price_idr"] <= 8_000_000),
        ("Lenovo minimal 5 juta dan maksimal 8 juta", 25, lambda item: 5_000_000 <= item["price_idr"] <= 8_000_000),
        ("Lenovo maksimal 8 juta dan minimal 5 juta", 25, lambda item: 5_000_000 <= item["price_idr"] <= 8_000_000),
        ("Lenovo maksimal Rp8 juta", 30, lambda item: item["price_idr"] <= 8_000_000),
        ("Lenovo minimal 15 juta dan maksimal 8 juta", 0, lambda item: False),
        ("8,5 juta ke bawah", 148, lambda item: item["price_idr"] <= 8_500_000),
        ("minimal RAM 16 GB", 141, lambda item: int(item["ram"].replace("GB", "")) >= 16),
        ("RAM maksimal 8 GB", 472, lambda item: int(item["ram"].replace("GB", "")) <= 8),
        ("Lenovo RAM maksimal 8 GB", 109, lambda item: int(item["ram"].replace("GB", "")) <= 8),
        ("RAM 128GB", 0, lambda item: False),
        ("SSD 0,5 TB", 95, lambda item: parse_storage_specs(item["storage"])["ssd_gb"] >= 500),
        ("SSD maksimal 256 GB", 358, lambda item: 0 < parse_storage_specs(item["storage"])["ssd_gb"] <= 256),
        ("HDD 1TB", 254, lambda item: parse_storage_specs(item["storage"])["hdd_gb"] >= 1000),
        ("Lenovo berat minimal 2 kg", 65, lambda item: parse_weight_kg(item["weight"]) >= 2.0),
        ("layar minimal 15 inci", 385, lambda item: _extract_inches(item["display"]) >= 15.0),
    ]

    for query, expected_cands, item_pred in cases:
        resp = client.get("/api/search", query_string={"q": query, "top": 100})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_candidates"] == expected_cands, f"Mismatch kandidat pada {query}: {data['constraints']}"
        for r in data["results"]:
            for cfg in _all_items_with_variants(r):
                assert item_pred(cfg), f"Pelanggaran constraint pada {query}: {cfg}"

    # Pastikan konfigurasi tepat Rp8.500.000 tidak terbuang oleh '8,5 juta ke bawah'
    out_85 = flask_app.engine.search("8,5 juta ke bawah", top_n=200)
    assert any(
        cfg["price_idr"] == 8_500_000
        for _, row in out_85.results.iterrows()
        for cfg in ([row] + list(row.get("variants") or []))
    )


def test_paket2_audit_brand_submodel_and_explicit_spec_queries():
    cases = [
        ("bukan Asus", 456, lambda r: r["brand"].lower() != "asus"),
        ("selain Asus", 456, lambda r: r["brand"].lower() != "asus"),
        ("jangan Asus", 456, lambda r: r["brand"].lower() != "asus"),
        ("Asus atau Lenovo", 240, lambda r: r["brand"].lower() in {"asus", "lenovo"}),
        ("Lenovo atau Asus", 240, lambda r: r["brand"].lower() in {"asus", "lenovo"}),
        ("MacBook Air", 1, lambda r: "macbook" in r["name"].lower() and "air" in r["name"].lower()),
        ("Lenovo ThinkPad T480", 0, lambda r: False),
        ("MacBook M3", 0, lambda r: False),
        ("wajib touchscreen", 88, lambda r: "touchscreen" in r["display"].lower()),
        ("tanpa touchscreen", 508, lambda r: "touchscreen" not in r["display"].lower()),
        (
            "laptop 2 in 1 touch screen",
            54,
            lambda r: "2 in 1" in r["category"].lower() and "touchscreen" in r["display"].lower(),
        ),
        ("RTX 4060", 0, lambda r: False),
        ("NVIDIA RTX 4060", 0, lambda r: False),
        ("laptop gaming RTX 4060 budget 20 juta", 0, lambda r: False),
        ("Windows 11", 0, lambda r: False),
        ("laptop dengan Windows 11", 0, lambda r: False),
        ("Intel Core i5", 214, lambda r: "intel core i5" in r["cpu"].lower()),
        ("Linux", 31, lambda r: r["os"].lower() == "linux"),
    ]

    for query, expected_cands, row_pred in cases:
        resp = client.get("/api/search", query_string={"q": query, "top": 100})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_candidates"] == expected_cands, f"Mismatch kandidat pada {query}: {data['constraints']}"
        for r in data["results"]:
            assert row_pred(r), f"Pelanggaran kartu utama pada {query}: {r}"

    d_al = client.get("/api/search", query_string={"q": "Asus atau Lenovo", "top": 100}).get_json()
    d_la = client.get("/api/search", query_string={"q": "Lenovo atau Asus", "top": 100}).get_json()
    assert [r["id"] for r in d_al["results"]] == [r["id"] for r in d_la["results"]]

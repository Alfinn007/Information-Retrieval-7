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

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DICT_JSON_PATH
from src.engine import LaptopRecommenderEngine, parse_storage_specs, parse_weight_kg
from src.expander import QueryExpander
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository


def _build_fixture_engine(rows):
    repo = LaptopRepository()
    repo.df = pd.DataFrame(rows)
    pre = TextPreprocessor()
    exp = QueryExpander(DICT_JSON_PATH)
    eng = LaptopRecommenderEngine(repo, pre, exp)
    eng.fit_index()
    return eng


def test_parse_storage_specs():
    s1 = parse_storage_specs("128GB SSD + 1TB HDD")
    assert s1["ssd_gb"] == 128 and s1["hdd_gb"] == 1000 and s1["total_gb"] == 1128

    s2 = parse_storage_specs("512GB SSD + 512GB SSD")
    assert s2["ssd_gb"] == 1024 and s2["hdd_gb"] == 0 and s2["total_gb"] == 1024

    s3 = parse_storage_specs("256GB Flash Storage")
    assert s3["flash_gb"] == 256 and s3["ssd_gb"] == 0 and s3["total_gb"] == 256

    s4 = parse_storage_specs("1.0TB Hybrid")
    assert s4["hybrid_gb"] == 1000 and s4["ssd_gb"] == 0 and s4["total_gb"] == 1000


def test_ssd_vs_total_storage_and_no_hdd():
    eng = _build_fixture_engine([
        {
            "id": "1", "brand": "BrandA", "name": "Model Hybrid", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "128GB SSD + 1TB HDD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.5kg", "price_idr": 8000000,
        },
        {
            "id": "2", "brand": "BrandB", "name": "Model DualSSD", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "512GB SSD + 512GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.5kg", "price_idr": 9000000,
        },
        {
            "id": "3", "brand": "BrandC", "name": "Model Flash", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "512GB Flash Storage", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.5kg", "price_idr": 7000000,
        },
    ])

    out_ssd = eng.search("SSD minimal 512 GB", top_n=5)
    assert list(out_ssd.results["id"]) == ["2"]

    out_total = eng.search("storage minimal 512 GB", top_n=5)
    assert set(out_total.results["id"]) == {"1", "2", "3"}

    out_no_hdd = eng.search("tanpa HDD", top_n=5)
    assert "1" not in set(out_no_hdd.results["id"])
    assert set(out_no_hdd.results["id"]) == {"2", "3"}


def test_weight_filtering_and_lightweight_preference():
    assert np.isnan(parse_weight_kg(""))
    assert np.isnan(parse_weight_kg(None))
    assert parse_weight_kg("1.37kg") == 1.37

    eng = _build_fixture_engine([
        {
            "id": "heavy", "brand": "BrandA", "name": "Kuliah Laptop A", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "2.2kg", "price_idr": 7000000,
        },
        {
            "id": "light", "brand": "BrandB", "name": "Kuliah Laptop B", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.2kg", "price_idr": 7000000,
        },
        {
            "id": "unknown_w", "brand": "BrandC", "name": "Kuliah Laptop C", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "", "price_idr": 7000000,
        },
    ])

    out_max = eng.search("berat maksimal 1,5 kg", top_n=5)
    assert list(out_max.results["id"]) == ["light"]

    out_pref = eng.search("buat kuliah yang ringan", top_n=5)
    assert out_pref.results.iloc[0]["id"] == "light"


def test_equal_price_equal_score_and_no_relax_on_empty():
    eng = _build_fixture_engine([
        {
            "id": "p1", "brand": "BrandA", "name": "Alpha 1", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.5kg", "price_idr": 6613000,
        },
        {
            "id": "p2", "brand": "BrandB", "name": "Beta 2", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.5kg", "price_idr": 6613000,
        },
    ])

    out = eng.search("laptop murah maksimal 8 juta", top_n=5)
    assert len(out.results) == 2
    assert out.results.iloc[0]["score"] == out.results.iloc[1]["score"]

    # Syarat mustahil tidak boleh melonggarkan mask
    out_empty = eng.search("maksimal 1 juta", top_n=5)
    assert out_empty.results.empty and out_empty.relaxed is False

    # Istilah tidak dikenal tidak boleh mengisi laptop acak
    out_unknown = eng.search("laptop merekxyztidakada999", top_n=5)
    assert out_unknown.results.empty


def test_decimal_weight_tokenization_does_not_match_heavy_laptops():
    eng = _build_fixture_engine([
        {
            "id": "light_12", "brand": "BrandA", "name": "FeatherBook", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "1.2kg", "price_idr": 8000000,
        },
        {
            "id": "heavy_22", "brand": "BrandB", "name": "BrickBook", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "2.2kg", "price_idr": 8000000,
        },
        {
            "id": "heavy_23", "brand": "BrandC", "name": "TankBook", "category": "Notebook",
            "display": "14.0 inch 1920x1080", "cpu": "Intel Core i5 8250U", "ram": "8GB",
            "storage": "256GB SSD", "gpu": "Intel UHD 620", "os": "Windows 10",
            "weight": "2.3kg", "price_idr": 8000000,
        },
    ])

    analyzer = eng.vectorizer.build_analyzer()
    assert analyzer("1.2kg") == ["1.2kg"]
    assert set(analyzer("1.2kg")).isdisjoint(set(analyzer("2.2kg")))
    assert set(analyzer("1.2kg")).isdisjoint(set(analyzer("2kg")))

    out = eng.search("laptop ringan", top_n=5)
    assert not out.results.empty
    assert out.results.iloc[0]["id"] == "light_12"
    if len(out.results) > 1:
        assert out.results.iloc[0]["score"] > out.results.iloc[1]["score"]

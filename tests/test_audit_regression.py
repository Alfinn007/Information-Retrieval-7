import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DICT_JSON_PATH, LEGACY_CSV_PATH
from src.engine import LaptopRecommenderEngine, parse_storage_specs, parse_weight_kg
from src.expander import QueryExpander
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository


@pytest.fixture(scope="module")
def catalog_engine():
    repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH)
    eng = LaptopRecommenderEngine(repo, TextPreprocessor(), QueryExpander(DICT_JSON_PATH))
    eng.fit_index()
    return eng


def _build_ground_truth_oracle(df: pd.DataFrame):
    price = df["price_idr"].astype(int).to_numpy()
    brand = df["brand"].astype(str).str.strip().str.lower()
    name = df["name"].astype(str).str.strip().str.lower()
    cpu = df["cpu"].astype(str).str.strip().str.lower()
    os_col = df["os"].astype(str).str.strip().str.lower()
    disp = df["display"].astype(str).str.strip().str.lower()
    cat = df["category"].astype(str).str.strip().str.lower()
    ram = pd.to_numeric(df["ram"].astype(str).str.extract(r"(\d+)")[0], errors="coerce").fillna(0).to_numpy()
    weight = df["weight"].apply(parse_weight_kg).to_numpy(dtype=float)
    inches = pd.to_numeric(df["display"].astype(str).str.extract(r"(\d+(?:\.\d+)?)")[0], errors="coerce").to_numpy(dtype=float)

    stor = df["storage"].apply(parse_storage_specs)
    ssd = stor.apply(lambda d: d["ssd_gb"]).to_numpy(dtype=int)
    hdd = stor.apply(lambda d: d["hdd_gb"]).to_numpy(dtype=int)

    lenovo = (brand == "lenovo").to_numpy()
    has_touch = disp.str.contains("touchscreen", regex=False).to_numpy()
    is_conv = cat.str.contains(r"2 in 1|convertible", regex=True).to_numpy()
    is_gaming = (cat == "gaming").to_numpy()
    impossible = price < 0

    return [
        # Harga (30)
        ("maksimal 8 juta", price <= 8_000_000),
        ("maks 8jt", price <= 8_000_000),
        ("maksimal Rp8.000.000", price <= 8_000_000),
        ("maksimal 8000000", price <= 8_000_000),
        ("budget 8 juta", price <= 8_000_000),
        ("MAKSIMAL    8 JUTA", price <= 8_000_000),
        ("laptop harga maksimal 8 juta", price <= 8_000_000),
        ("maksimal 8 juta dong", price <= 8_000_000),
        ("maksimal Rp8 juta", price <= 8_000_000),
        ("budget Rp 8 juta", price <= 8_000_000),
        ("budget saya 8 juta", price <= 8_000_000),
        ("maksimal 8.000.000", price <= 8_000_000),
        ("8 juta ke bawah", price <= 8_000_000),
        ("≤ 8 juta", price <= 8_000_000),
        ("5–8 juta", (price >= 5_000_000) & (price <= 8_000_000)),
        ("5 sampai 8 juta", (price >= 5_000_000) & (price <= 8_000_000)),
        ("minimal 5 juta dan maksimal 8 juta", (price >= 5_000_000) & (price <= 8_000_000)),
        ("antara 5 dan 8 juta", (price >= 5_000_000) & (price <= 8_000_000)),
        ("Lenovo 5-8 juta", lenovo & (price >= 5_000_000) & (price <= 8_000_000)),
        ("Lenovo minimal 5 juta dan maksimal 8 juta", lenovo & (price >= 5_000_000) & (price <= 8_000_000)),
        ("Lenovo maksimal 8 juta dan minimal 5 juta", lenovo & (price >= 5_000_000) & (price <= 8_000_000)),
        ("Lenovo maksimal 8 juta", lenovo & (price <= 8_000_000)),
        ("Lenovo maksimal Rp8 juta", lenovo & (price <= 8_000_000)),
        ("Lenovo tidak lebih dari 8 juta", lenovo & (price <= 8_000_000)),
        ("Lenovo minimal 15 juta dan maksimal 8 juta", impossible),
        ("di bawah Rp8.500.000", price < 8_500_000),
        ("maksimal Rp8.500.000", price <= 8_500_000),
        ("8,5 juta ke bawah", price <= 8_500_000),
        ("7,5 juta", (price >= 6_000_000) & (price <= 9_000_000)),
        ("7.5 juta", (price >= 6_000_000) & (price <= 9_000_000)),
        # Merek / seri (10)
        ("bukan Asus", (brand != "asus").to_numpy()),
        ("selain Asus", (brand != "asus").to_numpy()),
        ("jangan Asus", (brand != "asus").to_numpy()),
        ("Asus atau Lenovo", brand.isin(["asus", "lenovo"]).to_numpy()),
        ("Lenovo atau Asus", brand.isin(["asus", "lenovo"]).to_numpy()),
        ("ThinkPad RAM 16 GB", name.str.contains(r"\bthinkpad\b", regex=True).to_numpy() & (ram >= 16)),
        ("laptop macbook", name.str.contains(r"\bmacbook\b", regex=True).to_numpy()),
        ("MacBook Air", (name.str.contains(r"\bmacbook\b", regex=True) & name.str.contains(r"\bair\b", regex=True)).to_numpy()),
        ("Lenovo ThinkPad T480", impossible),
        ("MacBook M3", impossible),
        # RAM / drive (14)
        ("RAM 16 GB", ram >= 16),
        ("minimal RAM 16 GB", ram >= 16),
        ("RAM maksimal 8 GB", ram <= 8),
        ("Lenovo RAM maksimal 8 GB", lenovo & (ram <= 8)),
        ("RAM 128GB", ram >= 128),
        ("SSD 512GB", ssd >= 512),
        ("512 GB SSD", ssd >= 512),
        ("SSD 0,5 TB", ssd >= 500),
        ("SSD 0.5 TB", ssd >= 500),
        ("SSD maksimal 256 GB", (ssd > 0) & (ssd <= 256)),
        ("SSD 512 GB RAM 8 GB", (ssd >= 512) & (ram >= 8)),
        ("RAM 8GB SSD 512GB", (ssd >= 512) & (ram >= 8)),
        ("HDD 1TB", hdd >= 1000),
        ("tanpa HDD maksimal 10 juta", (hdd == 0) & (price <= 10_000_000)),
        # Berat / layar (9)
        ("berat maksimal 1,5 kg", np.isfinite(weight) & (weight <= 1.5)),
        ("berat maksimal 1.5 kg", np.isfinite(weight) & (weight <= 1.5)),
        ("berat di bawah 1,5 kg", np.isfinite(weight) & (weight < 1.5)),
        ("Lenovo berat minimal 2 kg", lenovo & np.isfinite(weight) & (weight >= 2.0)),
        ("layar minimal 15 inci", np.isfinite(inches) & (inches >= 15.0)),
        ("layar 14 inci", np.isfinite(inches) & (np.abs(inches - 14.0) <= 0.6)),
        ("wajib touchscreen", has_touch),
        ("tanpa touchscreen", ~has_touch),
        ("laptop 2 in 1 touch screen", is_conv & has_touch),
        # CPU / GPU / OS (7)
        ("RTX 4060", impossible),
        ("NVIDIA RTX 4060", impossible),
        ("laptop gaming RTX 4060 budget 20 juta", impossible),
        ("Windows 11", impossible),
        ("laptop dengan Windows 11", impossible),
        ("Intel Core i5", cpu.str.contains(r"\bintel\s+core\s+i5\b", regex=True).to_numpy()),
        ("Linux", (os_col == "linux").to_numpy()),
        # Kategori (1)
        ("bukan laptop gaming", ~is_gaming),
    ]


_ORACLE_DF = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH).df
_AUDIT_CASES = _build_ground_truth_oracle(_ORACLE_DF)


@pytest.mark.parametrize("query,mask", _AUDIT_CASES, ids=[q for q, _ in _AUDIT_CASES])
def test_audit_71_queries_exact_config_ids(catalog_engine, query, mask):
    df = catalog_engine.repo.df
    expected_rows = df.loc[mask]
    expected_ids = set(expected_rows["id"].astype(str).tolist())
    expected_models = set(
        zip(
            expected_rows["brand"].astype(str).str.strip().str.lower(),
            expected_rows["name"].astype(str).str.strip().str.lower(),
        )
    )

    out = catalog_engine.search(query, top_n=1000)
    got_ids = set()
    for _, row in out.results.iterrows():
        got_ids.add(str(row["id"]))
        for v in (row.get("variants") or []):
            got_ids.add(str(v["id"]))

    assert out.total_candidates == len(expected_models), (
        f"Jumlah model tidak cocok untuk '{query}': dapat {out.total_candidates}, seharusnya {len(expected_models)}"
    )
    assert got_ids == expected_ids, (
        f"Himpunan ID konfigurasi tidak cocok untuk '{query}' "
        f"(hilang={len(expected_ids - got_ids)}, berlebih={len(got_ids - expected_ids)})"
    )


def test_semantic_query_pairs_return_identical_config_ids(catalog_engine):
    groups = [
        [
            "Lenovo 5-8 juta",
            "Lenovo minimal 5 juta dan maksimal 8 juta",
            "Lenovo maksimal 8 juta dan minimal 5 juta",
        ],
        [
            "maksimal 8 juta",
            "laptop harga maksimal 8 juta",
            "maksimal 8 juta dong",
            "maksimal Rp8 juta",
            "budget Rp 8 juta",
            "budget saya 8 juta",
            "maksimal 8.000.000",
            "≤ 8 juta",
        ],
        ["bukan Asus", "selain Asus", "jangan Asus"],
        ["Asus atau Lenovo", "Lenovo atau Asus"],
        ["SSD 0,5 TB", "SSD 0.5 TB"],
        ["RAM 16 GB", "minimal RAM 16 GB"],
    ]

    for group in groups:
        baseline_out = catalog_engine.search(group[0], top_n=1000)
        baseline_ids = sorted(
            [str(r["id"]) for _, r in baseline_out.results.iterrows()]
            + [str(v["id"]) for _, r in baseline_out.results.iterrows() for v in (r.get("variants") or [])]
        )
        for q in group[1:]:
            other_out = catalog_engine.search(q, top_n=1000)
            other_ids = sorted(
                [str(r["id"]) for _, r in other_out.results.iterrows()]
                + [str(v["id"]) for _, r in other_out.results.iterrows() for v in (r.get("variants") or [])]
            )
            assert other_ids == baseline_ids, f"'{q}' harus menghasilkan ID yang sama persis dengan '{group[0]}'"

"""
Runner eksperimen query expansion (use_expansion=True vs False).
Menghasilkan:
- evaluation/expansion_results.csv
- evaluation/expansion_summary.csv
- evaluation/annotation_sheet.csv (lembar penilaian manusia tanpa label asal mode)
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DICT_JSON_PATH, LEGACY_CSV_PATH, SCRAPED_CSV_PATH
from src.engine import LaptopRecommenderEngine, parse_storage_specs, parse_weight_kg
from src.evaluator import SystemEvaluator
from src.expander import QueryExpander
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository

# 24 kueri Indonesia:
# - 6 kueri contoh website
# - kebutuhan sehari-hari, identitas produk, spesifikasi, campuran, kasus tanpa hasil,
#   serta parafrase yang tidak dipakai saat menyetel aturan
EVAL_QUERIES = [
    # 6 kueri contoh website
    "laptop gaming murah",
    "edit video 16gb 15 inch",
    "kuliah ringan di bawah 8 juta",
    "coding ssd 512gb",
    "laptop 2 in 1 touch screen",
    "laptop macbook",
    # Kebutuhan sehari-hari & parafrase baru
    "buat kuliah, nggak buat gaming",
    "bukan laptop gaming",
    "laptop kerja kantoran tahan lama",
    "untuk mahasiswa desain grafis",
    "laptop buat anak sekolah daring hemat",
    "perangkat ringan buat dibawa bepergian",
    # Identitas produk & campuran
    "ThinkPad RAM 16 GB",
    "Asus ROG gaming",
    "Dell XPS layar 15 inch",
    "Lenovo ThinkPad tanpa HDD",
    # Spesifikasi & harga beragam
    "ngoding budget 8 juta",
    "laptop maksimal 8000000",
    "laptop 7,5 juta ssd 256gb",
    "kisaran 10 juta ram 8gb",
    "berat maksimal 1,5 kg ssd 256gb",
    "yang paling murah di bawah 8 juta",
    # Kasus tanpa hasil (syarat mustahil)
    "gaming maksimal 5 juta",
    "macbook maksimal 5 juta",
]


def count_violations(row: pd.Series, constraints) -> int:
    violations = 0
    price = int(row["price_idr"])
    if constraints.price_min is not None:
        ok = price >= constraints.price_min if constraints.price_min_inclusive else price > constraints.price_min
        if not ok:
            violations += 1
    if constraints.price_max is not None:
        ok = price <= constraints.price_max if constraints.price_max_inclusive else price < constraints.price_max
        if not ok:
            violations += 1

    ram_match = pd.Series([str(row["ram"])]).str.extract(r"(\d+)")[0].iloc[0]
    ram_val = int(ram_match) if pd.notna(ram_match) else 0
    if constraints.ram_min is not None:
        ok = ram_val >= constraints.ram_min if constraints.ram_min_inclusive else ram_val > constraints.ram_min
        if not ok:
            violations += 1

    specs = parse_storage_specs(str(row["storage"]))
    if constraints.ssd_min_gb is not None:
        ok = specs["ssd_gb"] >= constraints.ssd_min_gb if constraints.ssd_min_inclusive else specs["ssd_gb"] > constraints.ssd_min_gb
        if not ok:
            violations += 1
    if constraints.storage_min_gb is not None:
        ok = specs["total_gb"] >= constraints.storage_min_gb if constraints.storage_min_inclusive else specs["total_gb"] > constraints.storage_min_gb
        if not ok:
            violations += 1
    if constraints.exclude_hdd and specs["hdd_gb"] > 0:
        violations += 1

    w_val = parse_weight_kg(row["weight"])
    if constraints.weight_max_kg is not None:
        if pd.isna(w_val):
            violations += 1
        else:
            ok = w_val <= constraints.weight_max_kg if constraints.weight_max_inclusive else w_val < constraints.weight_max_kg
            if not ok:
                violations += 1

    if constraints.exclude_gaming and str(row["category"]).strip().lower() == "gaming":
        violations += 1

    return violations


def main():
    out_dir = Path(__file__).resolve().parent
    preprocessor = TextPreprocessor()
    expander = QueryExpander(DICT_JSON_PATH)
    repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH).append_scraped_csv(SCRAPED_CSV_PATH)
    engine = LaptopRecommenderEngine(repo, preprocessor, expander)
    engine.fit_index()

    k = 5
    all_rows = []
    summary_rows = []
    pool_map = {}

    for query in EVAL_QUERIES:
        ids_by_mode = {}
        for mode_name, use_exp in [("no_expansion", False), ("with_expansion", True)]:
            out = engine.search(query, top_n=k, use_expansion=use_exp)
            df_res = out.results
            ids_by_mode[mode_name] = [str(x) for x in df_res["id"].tolist()] if not df_res.empty else []

            violations = 0
            unique_models = set()
            for rank, (_, row) in enumerate(df_res.iterrows(), start=1):
                violations += count_violations(row, out.constraints)
                unique_models.add((str(row["brand"]).strip().lower(), str(row["name"]).strip().lower()))
                pid = str(row["id"])
                all_rows.append({
                    "query": query,
                    "mode": mode_name,
                    "rank": rank,
                    "product_id": pid,
                    "brand": row["brand"],
                    "name": row["name"],
                    "category": row["category"],
                    "ram": row["ram"],
                    "storage": row["storage"],
                    "gpu": row["gpu"],
                    "weight": row["weight"],
                    "price_idr": int(row["price_idr"]),
                    "score": float(row["score"]),
                })
                pool_key = (query, pid)
                if pool_key not in pool_map:
                    sort_hash = hashlib.md5(f"{query}::{pid}".encode("utf-8")).hexdigest()
                    pool_map[pool_key] = {
                        "query": query,
                        "product_id": pid,
                        "brand": row["brand"],
                        "name": row["name"],
                        "category": row["category"],
                        "cpu": row["cpu"],
                        "ram": row["ram"],
                        "storage": row["storage"],
                        "gpu": row["gpu"],
                        "weight": row["weight"],
                        "price_idr": int(row["price_idr"]),
                        "relevance_label": "",
                        "_order": sort_hash,
                    }

            summary_rows.append({
                "query": query,
                "mode": mode_name,
                "returned_count": len(df_res),
                "total_candidates": out.total_candidates,
                "constraint_violations": violations,
                "unique_models_top5": len(unique_models),
            })

        overlap = SystemEvaluator.top_k_overlap(ids_by_mode["no_expansion"], ids_by_mode["with_expansion"], k=k)
        for s_row in summary_rows[-2:]:
            s_row["overlap_top5_count"] = overlap["overlap_count"]
            s_row["overlap_top5_jaccard"] = overlap["jaccard"]

    df_results = pd.DataFrame(all_rows)
    df_summary = pd.DataFrame(summary_rows)
    df_pool = pd.DataFrame(sorted(pool_map.values(), key=lambda x: (x["query"], x["_order"])))
    if not df_pool.empty:
        df_pool = df_pool.drop(columns=["_order"])

    df_results.to_csv(out_dir / "expansion_results.csv", index=False)
    df_summary.to_csv(out_dir / "expansion_summary.csv", index=False)
    df_pool.to_csv(out_dir / "annotation_sheet.csv", index=False)

    print(f"[+] Tersimpan {len(df_results)} baris hasil ke evaluation/expansion_results.csv")
    print(f"[+] Tersimpan {len(df_summary)} baris ringkasan ke evaluation/expansion_summary.csv")
    print(f"[+] Tersimpan {len(df_pool)} kandidat unik ke evaluation/annotation_sheet.csv (mode disembunyikan)")
    print(f"[+] Total pelanggaran syarat wajib: {df_summary['constraint_violations'].sum()}")


if __name__ == "__main__":
    main()

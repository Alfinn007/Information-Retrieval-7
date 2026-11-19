"""
Runner eksperimen query expansion (use_expansion=True vs False).
Menghasilkan:
- evaluation/expansion_results.csv
- evaluation/expansion_summary.csv
- evaluation/annotation_sheet.csv (lembar penilaian manusia tanpa label asal mode)
"""
import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import DICT_JSON_PATH, LEGACY_CSV_PATH, SCRAPED_CSV_PATH
from src.constraints import SCREEN_TOLERANCE
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

IMPOSSIBLE_QUERIES = {
    "gaming maksimal 5 juta",
    "macbook maksimal 5 juta",
}
FEASIBLE_QUERIES = [q for q in EVAL_QUERIES if q not in IMPOSSIBLE_QUERIES]


def load_existing_labels(sheet_path: Path) -> Dict[Tuple[str, str], str]:
    """Muat label penilai manusia yang sudah terisi agar tidak terhapus saat runner dijalankan ulang."""
    if not sheet_path.exists():
        return {}
    try:
        df_old = pd.read_csv(sheet_path, dtype=str, keep_default_na=False)
    except Exception:
        return {}
    required_cols = {"query", "product_id", "relevance_label"}
    if df_old.empty or not required_cols.issubset(df_old.columns):
        return {}

    labels: Dict[Tuple[str, str], str] = {}
    for _, row in df_old.iterrows():
        val = str(row["relevance_label"]).strip()
        if val != "":
            labels[(str(row["query"]).strip(), str(row["product_id"]).strip())] = val
    return labels


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
    if getattr(constraints, "ram_max", None) is not None:
        ok = ram_val <= constraints.ram_max if constraints.ram_max_inclusive else ram_val < constraints.ram_max
        if not ok:
            violations += 1

    specs = parse_storage_specs(str(row["storage"]))
    if constraints.ssd_min_gb is not None:
        ok = specs["ssd_gb"] >= constraints.ssd_min_gb if constraints.ssd_min_inclusive else specs["ssd_gb"] > constraints.ssd_min_gb
        if not ok:
            violations += 1
    if getattr(constraints, "ssd_max_gb", None) is not None:
        ok = specs["ssd_gb"] > 0 and (
            specs["ssd_gb"] <= constraints.ssd_max_gb if constraints.ssd_max_inclusive else specs["ssd_gb"] < constraints.ssd_max_gb
        )
        if not ok:
            violations += 1
    if getattr(constraints, "hdd_min_gb", None) is not None:
        ok = specs["hdd_gb"] >= constraints.hdd_min_gb if constraints.hdd_min_inclusive else specs["hdd_gb"] > constraints.hdd_min_gb
        if not ok:
            violations += 1
    if getattr(constraints, "hdd_max_gb", None) is not None:
        ok = specs["hdd_gb"] > 0 and (
            specs["hdd_gb"] <= constraints.hdd_max_gb if constraints.hdd_max_inclusive else specs["hdd_gb"] < constraints.hdd_max_gb
        )
        if not ok:
            violations += 1
    if constraints.storage_min_gb is not None:
        ok = specs["total_gb"] >= constraints.storage_min_gb if constraints.storage_min_inclusive else specs["total_gb"] > constraints.storage_min_gb
        if not ok:
            violations += 1
    if getattr(constraints, "storage_max_gb", None) is not None:
        ok = specs["total_gb"] > 0 and (
            specs["total_gb"] <= constraints.storage_max_gb if constraints.storage_max_inclusive else specs["total_gb"] < constraints.storage_max_gb
        )
        if not ok:
            violations += 1
    if constraints.exclude_hdd and specs["hdd_gb"] > 0:
        violations += 1

    w_val = parse_weight_kg(row["weight"])
    if getattr(constraints, "weight_min_kg", None) is not None:
        if pd.isna(w_val):
            violations += 1
        else:
            ok = w_val >= constraints.weight_min_kg if constraints.weight_min_inclusive else w_val > constraints.weight_min_kg
            if not ok:
                violations += 1
    if constraints.weight_max_kg is not None:
        if pd.isna(w_val):
            violations += 1
        else:
            ok = w_val <= constraints.weight_max_kg if constraints.weight_max_inclusive else w_val < constraints.weight_max_kg
            if not ok:
                violations += 1

    disp_str = str(row.get("display", "")).lower()
    m_in = re.search(r"(\d+(?:\.\d+)?)", disp_str)
    inches = float(m_in.group(1)) if m_in else float("nan")
    if getattr(constraints, "screen_inch", None) is not None:
        if pd.isna(inches) or abs(inches - constraints.screen_inch) > SCREEN_TOLERANCE:
            violations += 1
    if getattr(constraints, "screen_min_inch", None) is not None:
        if pd.isna(inches):
            violations += 1
        else:
            ok = inches >= constraints.screen_min_inch if constraints.screen_min_inclusive else inches > constraints.screen_min_inch
            if not ok:
                violations += 1
    if getattr(constraints, "screen_max_inch", None) is not None:
        if pd.isna(inches):
            violations += 1
        else:
            ok = inches <= constraints.screen_max_inch if constraints.screen_max_inclusive else inches < constraints.screen_max_inch
            if not ok:
                violations += 1

    brand_l = str(row.get("brand", "")).strip().lower()
    allowed_brands = [b.lower() for b in getattr(constraints, "allowed_brands", [])]
    if allowed_brands:
        if brand_l not in allowed_brands:
            violations += 1
    elif getattr(constraints, "required_brand", None):
        if brand_l != constraints.required_brand.lower():
            violations += 1
    excluded_brands = [b.lower() for b in getattr(constraints, "excluded_brands", [])]
    if brand_l in excluded_brands:
        violations += 1

    name_l = str(row.get("name", "")).strip().lower()
    if getattr(constraints, "required_family", None):
        fam_rx = re.compile(rf"(?<![a-z0-9]){re.escape(constraints.required_family.lower())}(?![a-z0-9])")
        if not fam_rx.search(name_l):
            violations += 1

    cat_l = str(row.get("category", "")).strip().lower()
    if constraints.exclude_gaming and cat_l == "gaming":
        violations += 1
    if getattr(constraints, "require_convertible", False) and not ("2 in 1" in cat_l or "convertible" in cat_l):
        violations += 1
    if getattr(constraints, "require_touchscreen", False) and "touchscreen" not in disp_str:
        violations += 1
    if getattr(constraints, "exclude_touchscreen", False) and "touchscreen" in disp_str:
        violations += 1

    os_l = str(row.get("os", "")).strip().lower()
    req_os = getattr(constraints, "required_os", None)
    if req_os:
        req_os_l = req_os.lower()
        if req_os_l in ("windows 10", "windows 8", "windows"):
            if not os_l.startswith(req_os_l):
                violations += 1
        elif req_os_l == "macos":
            if os_l not in ("macos", "mac os x"):
                violations += 1
        elif os_l != req_os_l:
            violations += 1

    return violations


def run_experiment(
    out_dir: Optional[Path] = None,
    engine: Optional[LaptopRecommenderEngine] = None,
) -> Dict[str, int]:
    target_dir = Path(out_dir) if out_dir is not None else Path(__file__).resolve().parent
    target_dir.mkdir(parents=True, exist_ok=True)

    if engine is None:
        preprocessor = TextPreprocessor()
        expander = QueryExpander(DICT_JSON_PATH)
        repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH).append_scraped_csv(SCRAPED_CSV_PATH)
        engine = LaptopRecommenderEngine(repo, preprocessor, expander)
        engine.fit_index()

    sheet_path = target_dir / "annotation_sheet.csv"
    existing_labels = load_existing_labels(sheet_path)

    k = 5
    all_rows = []
    summary_rows = []
    pool_map = {}

    for query in EVAL_QUERIES:
        ids_by_mode = {}
        query_type = "impossible" if query in IMPOSSIBLE_QUERIES else "feasible"
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
                    "display": row["display"],
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
                        "display": row["display"],
                        "cpu": row["cpu"],
                        "ram": row["ram"],
                        "storage": row["storage"],
                        "gpu": row["gpu"],
                        "weight": row["weight"],
                        "price_idr": int(row["price_idr"]),
                        "relevance_label": existing_labels.get((query, pid), ""),
                        "_order": sort_hash,
                    }

            summary_rows.append({
                "query": query,
                "query_type": query_type,
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

    df_results.to_csv(target_dir / "expansion_results.csv", index=False)
    df_summary.to_csv(target_dir / "expansion_summary.csv", index=False)
    df_pool.to_csv(sheet_path, index=False)

    preserved_count = int((df_pool["relevance_label"].astype(str).str.strip() != "").sum()) if not df_pool.empty else 0
    total_violations = int(df_summary["constraint_violations"].sum()) if not df_summary.empty else 0

    return {
        "results_count": len(df_results),
        "summary_count": len(df_summary),
        "pool_count": len(df_pool),
        "preserved_labels": preserved_count,
        "total_violations": total_violations,
    }


def main():
    stats = run_experiment()
    print(f"[+] Tersimpan {stats['results_count']} baris hasil ke evaluation/expansion_results.csv")
    print(f"[+] Tersimpan {stats['summary_count']} baris ringkasan ke evaluation/expansion_summary.csv")
    print(f"[+] Tersimpan {stats['pool_count']} kandidat unik ke evaluation/annotation_sheet.csv (mode disembunyikan)")
    print(f"[+] Label penilai lama yang dipertahankan: {stats['preserved_labels']}")
    print(f"[+] Total pelanggaran syarat wajib: {stats['total_violations']}")


if __name__ == "__main__":
    main()

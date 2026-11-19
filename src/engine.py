import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.constraints import Constraints, SCREEN_TOLERANCE, parse_constraints
from src.expander import QueryExpander
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository

OUTPUT_COLUMNS = [
    'id', 'brand', 'name', 'category', 'display', 'cpu', 'ram', 'storage',
    'gpu', 'os', 'weight', 'price_idr', 'score', 'expanded_query',
    'match_reasons', 'variants',
]

CANDIDATE_PRODUCT_FAMILIES = [
    'macbook', 'thinkpad', 'ideapad', 'yoga', 'legion',
    'xps', 'inspiron', 'latitude', 'precision', 'alienware', 'vostro',
    'elitebook', 'probook', 'pavilion', 'spectre', 'envy', 'zbook', 'omen',
    'zenbook', 'vivobook', 'rog', 'aspire', 'swift', 'nitro', 'predator',
    'chromebook', 'surface', 'gram', 'thinkbook',
]


def parse_storage_specs(storage_str: str) -> Dict[str, int]:
    """
    Memisahkan kapasitas drive dari string storage (mis. '128GB SSD + 1TB HDD')
    menjadi total_gb, ssd_gb, hdd_gb, flash_gb, dan hybrid_gb.
    Konvensi: 1 TB = 1000 GB (sesuai konvensi desimal dataset).
    """
    s = str(storage_str or '').lower()
    ssd_gb = 0
    hdd_gb = 0
    flash_gb = 0
    hybrid_gb = 0

    for segment in s.split('+'):
        seg = segment.strip()
        if not seg:
            continue
        m = re.search(r'(\d+(?:\.\d+)?)\s*(tb|gb)', seg)
        if not m:
            continue
        val = float(m.group(1))
        gb = int(round(val * 1000)) if m.group(2) == 'tb' else int(round(val))

        if 'ssd' in seg:
            ssd_gb += gb
        elif 'hdd' in seg:
            hdd_gb += gb
        elif 'flash' in seg or 'emmc' in seg:
            flash_gb += gb
        elif 'hybrid' in seg or 'sshd' in seg:
            hybrid_gb += gb

    total_gb = ssd_gb + hdd_gb + flash_gb + hybrid_gb
    return {
        'total_gb': total_gb,
        'ssd_gb': ssd_gb,
        'hdd_gb': hdd_gb,
        'flash_gb': flash_gb,
        'hybrid_gb': hybrid_gb,
    }


def _extract_total_storage_gb(storage_str: str) -> int:
    return parse_storage_specs(storage_str)['total_gb']


def parse_weight_kg(weight_str: Any) -> float:
    """Parse kolom weight (mis. '1.37kg') menjadi float kg; NaN jika tidak diketahui."""
    if weight_str is None or (isinstance(weight_str, float) and np.isnan(weight_str)):
        return float('nan')
    s = str(weight_str).strip().lower().replace(',', '.')
    m = re.search(r'(\d+(?:\.\d+)?)\s*kg\b', s)
    if not m:
        m = re.match(r'^(\d+(?:\.\d+)?)$', s)
    if not m:
        return float('nan')
    val = float(m.group(1))
    return val if val > 0 else float('nan')


def _min_rank_norm(values: np.ndarray, ascending: bool = True) -> np.ndarray:
    """
    Memberi skor [0..1] berbasis rank dengan tie-handling konsisten:
    nilai yang sama selalu mendapat skor rank yang persis sama.
    """
    n = len(values)
    if n <= 1:
        return np.ones(n, dtype=float)
    s = pd.Series(values)
    ranks = s.rank(method='min', ascending=ascending).to_numpy(dtype=float) - 1.0
    max_r = ranks.max()
    if max_r <= 0:
        return np.ones(n, dtype=float)
    return 1.0 - (ranks / max_r)


@dataclass
class SearchOutput:
    results: pd.DataFrame
    constraints: Constraints
    matched_phrases: List[str] = field(default_factory=list)
    expanded_query: str = "-"
    relaxed: bool = False
    total_candidates: int = 0


class LaptopRecommenderEngine:
    def __init__(self, repo: LaptopRepository, preprocessor: TextPreprocessor, expander: QueryExpander):
        self.repo = repo
        self.preprocessor = preprocessor
        self.expander = expander
        self.vectorizer = TfidfVectorizer(
            sublinear_tf=True,
            token_pattern=r'(?u)\b(?:[a-z0-9]{2,}|[0-9])(?:\.[a-z0-9]+)*\b',
        )
        self.tfidf_matrix = None

        self.ram_gb = None
        self.storage_gb = None
        self.ssd_gb = None
        self.hdd_gb = None
        self.flash_gb = None
        self.hybrid_gb = None
        self.weight_kg = None
        self.inches = None
        self.is_gaming_capable = None
        self.is_gaming_category = None
        self.has_dedicated_gpu = None
        self.quality_scores = None
        self.brand_low = None
        self.name_low = None
        self.known_brands: set = set()
        self.known_families: List[str] = []

    def fit_index(self):
        df = self.repo.build_corpus(self.preprocessor)
        self.tfidf_matrix = self.vectorizer.fit_transform(df['clean_document'])

        ram_num = pd.to_numeric(df['ram'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0).to_numpy(dtype=float)
        self.ram_gb = ram_num

        parsed_storage = df['storage'].apply(parse_storage_specs)
        self.storage_gb = parsed_storage.apply(lambda d: d['total_gb']).to_numpy(dtype=int)
        self.ssd_gb = parsed_storage.apply(lambda d: d['ssd_gb']).to_numpy(dtype=int)
        self.hdd_gb = parsed_storage.apply(lambda d: d['hdd_gb']).to_numpy(dtype=int)
        self.flash_gb = parsed_storage.apply(lambda d: d['flash_gb']).to_numpy(dtype=int)
        self.hybrid_gb = parsed_storage.apply(lambda d: d['hybrid_gb']).to_numpy(dtype=int)

        self.weight_kg = df['weight'].apply(parse_weight_kg).to_numpy(dtype=float)
        self.inches = pd.to_numeric(df['display'].astype(str).str.extract(r'(\d+(?:\.\d+)?)')[0], errors='coerce').to_numpy(dtype=float)

        gpu_low = df['gpu'].astype(str).str.lower()
        cat_low = df['category'].astype(str).str.lower()
        self.is_gaming_category = cat_low.eq('gaming').to_numpy()
        self.is_gaming_capable = (
            cat_low.eq('gaming') | gpu_low.str.contains(r'gtx|rtx|rx\s*5[678]0|radeon\s+r9|960m|965m|970m|980m', regex=True)
        ).to_numpy()
        self.has_dedicated_gpu = (
            self.is_gaming_capable | gpu_low.str.contains(r'quadro|geforce\s+mx|940mx|950m|radeon\s+r7|radeon\s+530', regex=True)
        ).to_numpy()

        has_ssd_or_flash = (self.ssd_gb > 0) | (self.flash_gb > 0)
        cpu_str = df['cpu'].astype(str).str.lower()
        cpu_tier = np.where(cpu_str.str.contains('i7|i9|ryzen 7|ryzen 9'), 1.0,
                   np.where(cpu_str.str.contains('i5|ryzen 5'), 0.75,
                   np.where(cpu_str.str.contains('i3|ryzen 3'), 0.50, 0.25)))
        disp_str = df['display'].astype(str).str.lower()
        fhd_score = np.where(disp_str.str.contains('1920x1080|2560x|3840x|4k|retina|fhd|ips'), 1.0, 0.50)
        ram_score = np.clip(ram_num / 16.0, 0.25, 1.0)
        ssd_score = np.where(has_ssd_or_flash, 1.0, 0.40)
        self.quality_scores = (0.35 * cpu_tier + 0.30 * ram_score + 0.20 * ssd_score + 0.15 * fhd_score)

        self.brand_low = df['brand'].astype(str).str.strip().str.lower().to_numpy()
        self.name_low = df['name'].astype(str).str.strip().str.lower().to_numpy()
        self.known_brands = {b for b in self.brand_low if b}

        all_names = " ".join(self.name_low)
        self.known_families = [
            fam for fam in CANDIDATE_PRODUCT_FAMILIES
            if re.search(rf'(?<![a-z0-9]){re.escape(fam)}(?![a-z0-9])', all_names)
        ]

    def _detect_product_identity(self, text_query: str, c: Constraints):
        q_low = text_query.lower()
        for fam in self.known_families:
            if re.search(rf'(?<![a-z0-9]){re.escape(fam)}(?![a-z0-9])', q_low):
                c.required_family = fam
                break
        for brand in sorted(self.known_brands, key=len, reverse=True):
            if re.search(rf'(?<![a-z0-9]){re.escape(brand)}(?![a-z0-9])', q_low):
                c.required_brand = brand
                break
        c.build_applied_filters()

    def _constraint_mask(self, c: Constraints) -> np.ndarray:
        df = self.repo.df
        mask = np.ones(len(df), dtype=bool)
        price = df['price_idr'].to_numpy(dtype=int)

        if c.price_min is not None:
            mask &= (price >= c.price_min) if c.price_min_inclusive else (price > c.price_min)
        if c.price_max is not None:
            mask &= (price <= c.price_max) if c.price_max_inclusive else (price < c.price_max)
        if c.ram_min is not None:
            mask &= (self.ram_gb >= c.ram_min) if c.ram_min_inclusive else (self.ram_gb > c.ram_min)
        if c.storage_min_gb is not None:
            mask &= (self.storage_gb >= c.storage_min_gb) if c.storage_min_inclusive else (self.storage_gb > c.storage_min_gb)
        if c.ssd_min_gb is not None:
            mask &= (self.ssd_gb >= c.ssd_min_gb) if c.ssd_min_inclusive else (self.ssd_gb > c.ssd_min_gb)
        if c.exclude_hdd:
            mask &= (self.hdd_gb == 0)
        if c.weight_max_kg is not None:
            valid_w = np.isfinite(self.weight_kg)
            mask &= valid_w & ((self.weight_kg <= c.weight_max_kg) if c.weight_max_inclusive else (self.weight_kg < c.weight_max_kg))
        if c.screen_inch is not None:
            valid_in = np.isfinite(self.inches)
            mask &= valid_in & (np.abs(self.inches - c.screen_inch) <= SCREEN_TOLERANCE)

        if c.required_brand:
            mask &= (self.brand_low == c.required_brand.lower())
        if c.required_family:
            fam_rx = re.compile(rf'(?<![a-z0-9]){re.escape(c.required_family.lower())}(?![a-z0-9])')
            fam_mask = np.array([bool(fam_rx.search(n)) for n in self.name_low], dtype=bool)
            mask &= fam_mask

        if c.exclude_gaming:
            mask &= ~self.is_gaming_category
        if c.require_gaming_gpu:
            mask &= self.is_gaming_capable
        elif c.require_creator_spec:
            mask &= self.has_dedicated_gpu

        return mask

    def _build_match_reasons(self, idx: int, c: Constraints) -> List[str]:
        row = self.repo.df.iloc[idx]
        reasons: List[str] = []
        if c.price_max is not None or c.price_min is not None:
            price_str = f"Rp{int(row['price_idr']):,}".replace(',', '.')
            reasons.append(f"Harga {price_str} sesuai batas")
        if c.ram_min is not None:
            reasons.append(f"RAM {int(self.ram_gb[idx])}GB memenuhi >= {c.ram_min}GB")
        if c.ssd_min_gb is not None:
            reasons.append(f"SSD {int(self.ssd_gb[idx])}GB memenuhi >= {c.ssd_min_gb}GB")
        elif c.storage_min_gb is not None:
            reasons.append(f"Storage {int(self.storage_gb[idx])}GB memenuhi >= {c.storage_min_gb}GB")
        if c.exclude_hdd:
            reasons.append("Tanpa HDD")
        if c.weight_max_kg is not None or c.prefer_lightweight:
            w = self.weight_kg[idx]
            if np.isfinite(w):
                reasons.append(f"Berat {w:g} kg")
        if c.screen_inch is not None and np.isfinite(self.inches[idx]):
            reasons.append(f"Layar {self.inches[idx]:g} inch")
        return reasons

    def search(
        self,
        query: str,
        top_n: int = 5,
        use_expansion: bool = True,
        use_constraints: bool = True,
        alpha: float = 0.5,
        group_variants: bool = True,
    ) -> SearchOutput:
        constraints, text_query = (
            parse_constraints(query) if use_constraints else (Constraints(), query)
        )
        if use_constraints:
            self._detect_product_identity(text_query, constraints)

        base_q = self.preprocessor.clean_text(text_query)
        if use_expansion and text_query:
            exp_raw, matched_phrases = self.expander.expand_with_matches(text_query, constraints=constraints)
        else:
            exp_raw, matched_phrases = "", []
        exp_q = self.preprocessor.clean_text(exp_raw) if exp_raw else ""

        exp_display = (base_q + " " + exp_q).strip()
        if not exp_display:
            exp_display = f"(Filter: {constraints.describe()})" if not constraints.is_empty else "-"

        q_vec = self.vectorizer.transform([base_q]) if base_q else None
        if q_vec is not None and exp_q:
            q_vec = q_vec + alpha * self.vectorizer.transform([exp_q])

        mask = self._constraint_mask(constraints)
        valid = np.where(mask)[0]

        if len(valid) == 0:
            return SearchOutput(
                results=pd.DataFrame(columns=OUTPUT_COLUMNS),
                constraints=constraints,
                matched_phrases=matched_phrases,
                expanded_query=exp_display,
                relaxed=False,
                total_candidates=0,
            )

        # Jika user mengetik istilah pencarian namun tidak ada token yang dikenal di korpus
        if base_q and (q_vec is None or q_vec.nnz == 0):
            return SearchOutput(
                results=pd.DataFrame(columns=OUTPUT_COLUMNS),
                constraints=constraints,
                matched_phrases=matched_phrases,
                expanded_query=exp_display,
                relaxed=False,
                total_candidates=0,
            )

        if q_vec is not None and q_vec.nnz > 0:
            sim_scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
            valid = valid[sim_scores[valid] > 0]
            if len(valid) == 0:
                return SearchOutput(
                    results=pd.DataFrame(columns=OUTPUT_COLUMNS),
                    constraints=constraints,
                    matched_phrases=matched_phrases,
                    expanded_query=exp_display,
                    relaxed=False,
                    total_candidates=0,
                )
            base_rel = sim_scores[valid]
        elif not constraints.is_empty:
            base_rel = self.quality_scores[valid]
        else:
            return SearchOutput(
                results=pd.DataFrame(columns=OUTPUT_COLUMNS),
                constraints=constraints,
                matched_phrases=matched_phrases,
                expanded_query=exp_display,
                relaxed=False,
                total_candidates=0,
            )

        valid_prices = self.repo.df['price_idr'].to_numpy(dtype=float)[valid]
        affordability = _min_rank_norm(valid_prices, ascending=True)

        valid_weights = self.weight_kg[valid]
        lightness = np.zeros(len(valid), dtype=float)
        finite_w_mask = np.isfinite(valid_weights)
        if finite_w_mask.any():
            lightness[finite_w_mask] = _min_rank_norm(valid_weights[finite_w_mask], ascending=True)

        if constraints.sort_cheapest_explicit:
            # Urutkan harga termurah dulu, relevansi sebagai tie-breaker
            order_local = np.lexsort((-base_rel, valid_prices))
            final_scores = affordability * 0.8 + base_rel * 0.2
        else:
            if q_vec is not None and q_vec.nnz > 0:
                if constraints.prefer_cheap and constraints.prefer_lightweight:
                    final_scores = 0.65 * base_rel + 0.20 * affordability + 0.15 * lightness
                elif constraints.prefer_cheap:
                    final_scores = 0.70 * base_rel + 0.30 * affordability
                elif constraints.prefer_lightweight:
                    final_scores = 0.80 * base_rel + 0.20 * lightness
                else:
                    final_scores = base_rel
            else:
                if constraints.prefer_cheap and constraints.prefer_lightweight:
                    final_scores = 0.50 * base_rel + 0.30 * affordability + 0.20 * lightness
                elif constraints.prefer_cheap:
                    final_scores = 0.50 * base_rel + 0.50 * affordability
                elif constraints.prefer_lightweight:
                    final_scores = 0.75 * base_rel + 0.25 * lightness
                else:
                    final_scores = 0.85 * base_rel + 0.15 * affordability
            order_local = np.argsort(-final_scores, kind='stable')

        ordered_indices = valid[order_local]
        ordered_scores = final_scores[order_local]

        if group_variants:
            grouped_indices: List[int] = []
            grouped_scores: List[float] = []
            variants_by_key: Dict[tuple, List[Dict[str, Any]]] = {}
            key_to_pos: Dict[tuple, int] = {}

            for idx, sc in zip(ordered_indices, ordered_scores):
                key = (self.brand_low[idx], self.name_low[idx])
                row = self.repo.df.iloc[idx]
                variant_obj = {
                    'id': str(row['id']),
                    'cpu': str(row['cpu']),
                    'ram': str(row['ram']),
                    'storage': str(row['storage']),
                    'gpu': str(row['gpu']),
                    'display': str(row['display']),
                    'weight': str(row['weight']),
                    'price_idr': int(row['price_idr']),
                    'score': round(float(sc), 4),
                }
                if key not in key_to_pos:
                    key_to_pos[key] = len(grouped_indices)
                    grouped_indices.append(idx)
                    grouped_scores.append(float(sc))
                    variants_by_key[key] = []
                else:
                    variants_by_key[key].append(variant_obj)

            total_candidates = len(grouped_indices)
            selected_indices = grouped_indices[:top_n]
            selected_scores = grouped_scores[:top_n]
            selected_variants = [
                variants_by_key[(self.brand_low[idx], self.name_low[idx])]
                for idx in selected_indices
            ]
        else:
            total_candidates = len(ordered_indices)
            selected_indices = list(ordered_indices[:top_n])
            selected_scores = [float(s) for s in ordered_scores[:top_n]]
            selected_variants = [[] for _ in selected_indices]

        if not selected_indices:
            return SearchOutput(
                results=pd.DataFrame(columns=OUTPUT_COLUMNS),
                constraints=constraints,
                matched_phrases=matched_phrases,
                expanded_query=exp_display,
                relaxed=False,
                total_candidates=0,
            )

        results = self.repo.df.iloc[selected_indices].copy()
        results['score'] = [round(s, 4) for s in selected_scores]
        results['expanded_query'] = exp_display
        results['match_reasons'] = [self._build_match_reasons(idx, constraints) for idx in selected_indices]
        results['variants'] = selected_variants

        return SearchOutput(
            results=results[OUTPUT_COLUMNS].reset_index(drop=True),
            constraints=constraints,
            matched_phrases=matched_phrases,
            expanded_query=exp_display,
            relaxed=False,
            total_candidates=total_candidates,
        )

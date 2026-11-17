import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.repository import LaptopRepository
from src.preprocessor import TextPreprocessor
from src.expander import QueryExpander
from src.constraints import Constraints, parse_constraints

OUTPUT_COLUMNS = [
    'id', 'brand', 'name', 'category', 'display', 'cpu', 'ram', 'storage',
    'gpu', 'os', 'weight', 'price_idr', 'score', 'expanded_query'
]


def _extract_total_storage_gb(storage_str: str) -> int:
    s = str(storage_str).lower()
    total = 0
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(tb|gb)', s):
        val = float(m.group(1))
        total += int(val * 1000) if m.group(2) == 'tb' else int(val)
    return total


class LaptopRecommenderEngine:
    def __init__(self, repo: LaptopRepository, preprocessor: TextPreprocessor, expander: QueryExpander):
        self.repo = repo
        self.preprocessor = preprocessor
        self.expander = expander
        self.vectorizer = TfidfVectorizer(sublinear_tf=True)
        self.tfidf_matrix = None
        self.ram_gb = None
        self.storage_gb = None
        self.inches = None
        self.is_gaming_capable = None
        self.has_dedicated_gpu = None
        self.quality_scores = None
        
        self.last_constraints = Constraints()
        self.last_matched = []
        self.last_relaxed = False

    def fit_index(self):
        df = self.repo.build_corpus(self.preprocessor)
        self.tfidf_matrix = self.vectorizer.fit_transform(df['clean_document'])
        
        ram_num = pd.to_numeric(df['ram'].str.extract(r'(\d+)')[0], errors='coerce').fillna(4).to_numpy()
        self.ram_gb = ram_num
        self.storage_gb = df['storage'].apply(_extract_total_storage_gb).to_numpy()
        self.inches = pd.to_numeric(df['display'].str.extract(r'^(\d+(?:\.\d+)?)')[0], errors='coerce').to_numpy()
        
        gpu_low = df['gpu'].str.lower()
        cat_low = df['category'].str.lower()
        self.is_gaming_capable = (
            cat_low.eq('gaming') | gpu_low.str.contains(r'gtx|rtx|rx\s*5[678]0|radeon\s+r9|960m|965m|970m|980m')
        ).to_numpy()
        self.has_dedicated_gpu = (
            self.is_gaming_capable | gpu_low.str.contains(r'quadro|geforce\s+mx|940mx|950m|radeon\s+r7|radeon\s+530')
        ).to_numpy()

        has_ssd = df['storage'].str.contains('SSD|Flash Storage', case=False, na=False).to_numpy()
        cpu_str = df['cpu'].str.lower()
        cpu_tier = np.where(cpu_str.str.contains('i7|i9|ryzen 7|ryzen 9'), 1.0,
                   np.where(cpu_str.str.contains('i5|ryzen 5'), 0.75,
                   np.where(cpu_str.str.contains('i3|ryzen 3'), 0.50, 0.25)))
        disp_str = df['display'].str.lower()
        fhd_score = np.where(disp_str.str.contains('1920x1080|2560x|3840x|4k|retina|fhd|ips'), 1.0, 0.50)
        ram_score = np.clip(ram_num / 16.0, 0.25, 1.0)
        ssd_score = np.where(has_ssd, 1.0, 0.40)
        self.quality_scores = (0.35 * cpu_tier + 0.30 * ram_score + 0.20 * ssd_score + 0.15 * fhd_score)

    def _constraint_mask(self, c: Constraints) -> np.ndarray:
        df = self.repo.df
        mask = np.ones(len(df), dtype=bool)
        price = df['price_idr'].to_numpy()
        
        if c.price_min is not None:
            mask &= price >= c.price_min
        if c.price_max is not None:
            mask &= price <= c.price_max
        if c.ram_min is not None:
            mask &= np.nan_to_num(self.ram_gb, nan=0) >= c.ram_min
        if c.storage_min_gb is not None:
            mask &= self.storage_gb >= c.storage_min_gb
        if c.screen_inch is not None:
            mask &= np.abs(np.nan_to_num(self.inches, nan=-99) - c.screen_inch) <= 0.6
        if c.require_gaming_gpu:
            mask &= self.is_gaming_capable
        elif c.require_creator_spec:
            mask &= self.has_dedicated_gpu
        return mask

    def search(self, query: str, top_n: int = 5, use_expansion: bool = True,
               use_constraints: bool = True, alpha: float = 0.5) -> pd.DataFrame:
        constraints, text_query = (parse_constraints(query) if use_constraints
                                   else (Constraints(), query))
        
        base_q = self.preprocessor.clean_text(text_query)
        exp_raw = self.expander.expansion_terms(text_query) if use_expansion else ""
        exp_q = self.preprocessor.clean_text(exp_raw) if exp_raw else ""

        self.last_constraints = constraints
        self.last_matched = self.expander.matched_phrases(text_query) if use_expansion else []

        q_vec = self.vectorizer.transform([base_q])
        if exp_q:
            q_vec = q_vec + alpha * self.vectorizer.transform([exp_q])

        mask = self._constraint_mask(constraints)
        self.last_relaxed = False
        
        if not mask.any():
            mask = np.ones(len(mask), dtype=bool)
            self.last_relaxed = True

        valid = np.where(mask)[0]

        if q_vec.nnz > 0:
            sim_scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
            scores = sim_scores.copy()
            if getattr(constraints, 'sort_cheapest', False) and len(valid) > 1:
                valid_prices = self.repo.df['price_idr'].to_numpy()[valid].astype(float)
                price_ranks = np.argsort(np.argsort(valid_prices))
                affordability = 1.0 - (price_ranks / (len(valid) - 1))
                scores[valid] = 0.50 * scores[valid] + 0.50 * affordability
        else:
            if not constraints.is_empty and len(valid) > 0:
                scores = np.zeros(len(self.repo.df), dtype=float)
                valid_prices = self.repo.df['price_idr'].to_numpy()[valid].astype(float)
                price_ranks = np.argsort(np.argsort(valid_prices))
                affordability = 1.0 - (price_ranks / max(len(valid) - 1, 1))
                if getattr(constraints, 'sort_cheapest', False):
                    scores[valid] = 0.40 * self.quality_scores[valid] + 0.60 * affordability
                else:
                    scores[valid] = 0.85 * self.quality_scores[valid] + 0.15 * affordability
            else:
                scores = np.zeros(len(self.repo.df), dtype=float)
                valid = np.array([], dtype=int)

        if len(valid) > 0:
            valid = valid[scores[valid] > 0]
            order = valid[np.argsort(-scores[valid], kind='stable')][:top_n]
        else:
            order = np.array([], dtype=int)

        if len(order) == 0:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)

        results = self.repo.df.iloc[order].copy()
        results['score'] = scores[order].round(4)
        
        exp_display = (base_q + " " + exp_q).strip()
        if not exp_display:
            exp_display = f"(Filter: {constraints.describe()})" if not constraints.is_empty else "-"
        results['expanded_query'] = exp_display
        return results[OUTPUT_COLUMNS]

import re
import pandas as pd
from pathlib import Path
from src.config import EURO_TO_IDR_RATE
from src.preprocessor import TextPreprocessor

SPEC_DEDUP_COLUMNS = [
    'brand', 'name', 'display', 'cpu', 'ram',
    'storage', 'gpu', 'os', 'weight', 'price_idr'
]


def _norm_cell(val) -> str:
    return re.sub(r'\s+', ' ', str(val or '').strip().lower())


class LaptopRepository:
    def __init__(self, euro_rate: float = EURO_TO_IDR_RATE):
        self.euro_rate = euro_rate
        self.df = pd.DataFrame()

    def _deduplicate_exact(self):
        if self.df.empty:
            return
        norm_df = pd.DataFrame({
            col: self.df[col].map(_norm_cell) if col != 'price_idr' else self.df[col].astype(int)
            for col in SPEC_DEDUP_COLUMNS
            if col in self.df.columns
        })
        keep_mask = ~norm_df.duplicated(keep='first')
        self.df = self.df.loc[keep_mask].reset_index(drop=True)

    def load_legacy_csv(self, filepath: Path):
        raw_df = pd.read_csv(filepath, encoding='latin1')
        standardized = pd.DataFrame({
            'id': raw_df['laptop_ID'].astype(str),
            'brand': raw_df['Company'].astype(str).str.strip(),
            'name': raw_df['Product'].astype(str).str.strip(),
            'category': raw_df['TypeName'].astype(str).str.strip(),
            'display': raw_df['Inches'].astype(str).str.strip() + " inch " + raw_df['ScreenResolution'].astype(str).str.strip(),
            'cpu': raw_df['Cpu'].astype(str).str.strip(),
            'ram': raw_df['Ram'].astype(str).str.strip(),
            'storage': raw_df['Memory'].astype(str).str.strip(),
            'gpu': raw_df['Gpu'].astype(str).str.strip(),
            'os': raw_df['OpSys'].astype(str).str.strip(),
            'weight': raw_df['Weight'].astype(str).str.strip(),
            'price_idr': (raw_df['Price_euros'] * self.euro_rate).astype(int)
        })
        self.df = pd.concat([self.df, standardized], ignore_index=True)
        self._deduplicate_exact()
        return self

    def append_scraped_csv(self, filepath: Path):
        if Path(filepath).exists():
            new_df = pd.read_csv(filepath)
            self.df = pd.concat([self.df, new_df], ignore_index=True)
            self._deduplicate_exact()
        return self

    def build_corpus(self, preprocessor: TextPreprocessor) -> pd.DataFrame:
        price_tier = self.df['price_idr'].apply(
            lambda p: "murah terjangkau entry" if p < 7500000 else ("menengah mid" if p <= 15000000 else "mahal sultan high end")
        )

        raw_docs = (
            self.df['brand'].astype(str) + " " + self.df['name'].astype(str) + " " + self.df['category'].astype(str) + " " +
            self.df['display'].astype(str) + " " + self.df['cpu'].astype(str) + " " + self.df['ram'].astype(str) + " " +
            self.df['storage'].astype(str) + " " + self.df['gpu'].astype(str) + " " + self.df['os'].astype(str) + " " +
            self.df['weight'].astype(str) + " " + price_tier
        )
        self.df['clean_document'] = raw_docs.apply(preprocessor.clean_text)
        return self.df

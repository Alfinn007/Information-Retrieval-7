import pandas as pd
from pathlib import Path
from src import preprocessor
from src import preprocessor
from src.config import EURO_TO_IDR_RATE
from src.preprocessor import TextPreprocessor

class LaptopRepository:
    def __init__(self, euro_rate: float = EURO_TO_IDR_RATE):
        self.euro_rate = euro_rate
        self.df = pd.DataFrame()

    def load_legacy_csv(self, filepath: Path):
        raw_df = pd.read_csv(filepath, encoding='latin1')
        standardized = pd.DataFrame({
            'id': raw_df['laptop_ID'].astype(str),
            'brand': raw_df['Company'],
            'name': raw_df['Product'],
            'category': raw_df['TypeName'],
            'display': raw_df['Inches'].astype(str) + " inch " + raw_df['ScreenResolution'],
            'cpu': raw_df['Cpu'],
            'ram': raw_df['Ram'],
            'storage': raw_df['Memory'],
            'gpu': raw_df['Gpu'],
            'os': raw_df['OpSys'],
            'weight': raw_df['Weight'],
            'price_idr': (raw_df['Price_euros'] * self.euro_rate).astype(int)
        })
        self.df = pd.concat([self.df, standardized], ignore_index=True)
        return self

    def append_scraped_csv(self, filepath: Path):
        if Path(filepath).exists():
            new_df = pd.read_csv(filepath)
            self.df = pd.concat([self.df, new_df], ignore_index=True)
            self.df.drop_duplicates(subset=['brand', 'name', 'cpu', 'ram', 'gpu'], inplace=True)
        return self

    def build_corpus(self, preprocessor: TextPreprocessor) -> pd.DataFrame:
    
        price_tier = self.df['price_idr'].apply(
            lambda p: "murah terjangkau entry" if p < 7500000 else ("menengah mid" if p <= 15000000 else "mahal Sultan high end")
        )

        raw_docs = (
            self.df['brand'] + " " + self.df['name'] + " " + self.df['category'] + " " +
            self.df['display'] + " " + self.df['cpu'] + " " + self.df['ram'] + " " +
            self.df['storage'] + " " + self.df['gpu'] + " " + self.df['os'] + " " +
            self.df['weight'] + " " + price_tier
        )
        self.df['clean_document'] = raw_docs.apply(preprocessor.clean_text)
        return self.df
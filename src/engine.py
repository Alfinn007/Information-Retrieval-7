import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.repository import LaptopRepository
from src.preprocessor import TextPreprocessor
from src.expander import QueryExpander

class LaptopRecommenderEngine:
    def __init__(self, repo: LaptopRepository, preprocessor: TextPreprocessor, expander: QueryExpander):
        self.repo = repo
        self.preprocessor = preprocessor
        self.expander = expander
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = None

    def fit_index(self):
        df = self.repo.build_corpus(self.preprocessor)
        self.tfidf_matrix = self.vectorizer.fit_transform(df['clean_document'])

    def search(self, query: str, top_n: int = 5, use_expansion: bool = True) -> pd.DataFrame:
        raw_q = self.expander.expand(query) if use_expansion else query
        clean_q = self.preprocessor.clean_text(raw_q)
        
        q_vec = self.vectorizer.transform([clean_q])
        scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
        
        top_idx = scores.argsort()[::-1][:top_n]
        results = self.repo.df.iloc[top_idx].copy()
        results['score'] = scores[top_idx].round(4)
        results['expanded_query'] = clean_q
        return results[['id', 'brand', 'name', 'category', 'cpu', 'ram', 'storage', 'gpu', 'price_idr', 'score', 'expanded_query']]
import re
from src.config import STOPWORDS_ID, TECH_NORMALIZATION_RULES

class TextPreprocessor:
    def __init__(self):
        self.rules = TECH_NORMALIZATION_RULES
        self.stopwords = STOPWORDS_ID

    def clean_text(self, text: str) -> str:
        text = str(text).lower()
        for pattern, replacement in self.rules.items():
            text = re.sub(pattern, replacement, text)
        text = re.sub(r'[^a-z0-9.\s]', ' ', text)
        tokens = [w for w in text.split() if w not in self.stopwords]
        return " ".join(tokens)
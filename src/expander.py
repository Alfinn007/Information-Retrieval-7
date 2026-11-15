import json
from pathlib import Path

class QueryExpander:
    def __init__(self, json_path: Path):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.dictionary = json.load(f)

    def expand(self, query: str) -> str:
        query_lower = query.lower()
        expanded_terms = [query_lower]
        for phrase, tech_specs in self.dictionary.items():
            if phrase in query_lower:
                expanded_terms.append(tech_specs)
        return " ".join(expanded_terms)
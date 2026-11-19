import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from src.intents import INTENT_SYNONYMS

CONTEXTUAL_CHEAP_SPECS = {
    "gaming": "gaming gtx geforce 1050 960m 950m rx 560 i5 ryzen5 8gb ssd fhd",
    "edit video": "ips fhd mx150 radeon i5 ryzen5 8gb 16gb ssd ultrabook notebook",
    "desain": "ips fhd mx150 radeon i5 ryzen5 8gb ssd ultrabook notebook",
    "coding": "i5 ryzen5 i3 8gb ssd fhd notebook ultrabook",
    "kuliah": "notebook i3 ryzen3 celeron pentium 4gb 8gb ssd murah terjangkau entry",
    "kantor": "notebook ultrabook i3 i5 8gb ssd fhd murah terjangkau",
}

PRODUCT_IDENTITY_TOKENS = {"macbook", "apple", "macos", "mac os", "imac", "chromebook"}

_HEAVY_WORDS = sorted(
    set(
        INTENT_SYNONYMS.get("gaming", [])
        + INTENT_SYNONYMS.get("edit video", [])
        + INTENT_SYNONYMS.get("desain", [])
        + INTENT_SYNONYMS.get("coding", [])
        + ["kencang", "cepat", "ngebut", "gahar"]
    ),
    key=len,
    reverse=True,
)
_HEAVY_WORDS_RX = re.compile(
    r'(?<![a-z0-9])(?:' + "|".join(re.escape(w.lower()) for w in _HEAVY_WORDS) + r')(?![a-z0-9])'
)


class QueryExpander:
    def __init__(self, json_path: Path):
        with open(json_path, 'r', encoding='utf-8') as f:
            base_dict = json.load(f)

        self.dictionary = dict(base_dict)

        for canonical, aliases in INTENT_SYNONYMS.items():
            if canonical in self.dictionary:
                spec = self.dictionary[canonical]
                for alias in aliases:
                    self.dictionary.setdefault(alias, spec)

        for uc_key, combo_spec in CONTEXTUAL_CHEAP_SPECS.items():
            for uc_alias in INTENT_SYNONYMS.get(uc_key, [uc_key]):
                for cheap_alias in INTENT_SYNONYMS["murah"]:
                    self.dictionary[f"{uc_alias} {cheap_alias}"] = combo_spec
                    self.dictionary[f"{cheap_alias} {uc_alias}"] = combo_spec
                    self.dictionary[f"{uc_alias} yang {cheap_alias}"] = combo_spec

        for key in list(self.dictionary.keys()):
            words = key.split()
            if len(words) == 2:
                self.dictionary.setdefault(f"{words[1]} {words[0]}", self.dictionary[key])

        self._keys = sorted(self.dictionary.keys(), key=len, reverse=True)
        self._keys_lower = [(k, k.lower()) for k in self._keys]
        self._pattern_cache = {}

    def matched_phrases(self, query: str) -> List[str]:
        """Daftar frasa kamus yang cocok pada query (tanpa tumpang tindih)."""
        remaining = query.lower()
        matched = []
        for key, key_low in self._keys_lower:
            if key_low not in remaining:
                continue
            pattern = self._pattern_cache.get(key)
            if pattern is None:
                pattern = re.compile(r'(?<![a-z0-9])' + re.escape(key_low) + r'(?![a-z0-9])')
                self._pattern_cache[key] = pattern
            if pattern.search(remaining):
                matched.append(key)
                remaining = pattern.sub(' ' * len(key), remaining)
        return matched

    def expand_with_matches(
        self,
        query: str,
        constraints=None,
    ) -> Tuple[str, List[str]]:
        """
        Mengembalikan (expansion_terms, matched_phrases) dalam satu kali pencocokan frasa.
        Menghormati syarat eksplisit user (RAM, storage, SSD, tanpa HDD, dan negasi gaming).
        """
        query_lower = query.lower()
        matched = self.matched_phrases(query_lower)

        user_ram_val = 0
        if constraints is not None and getattr(constraints, 'ram_min', None):
            user_ram_val = int(constraints.ram_min)
        else:
            user_ram_match = re.search(r'\b(2|4|6|8|12|16|24|32|64)\s*gb\b', query_lower)
            user_ram_val = int(user_ram_match.group(1)) if user_ram_match else 0

        user_has_ram = user_ram_val > 0 or bool(
            constraints is not None and getattr(constraints, 'ram_max', None)
        )
        user_has_storage = bool(
            (constraints is not None and (
                getattr(constraints, 'storage_min_gb', None)
                or getattr(constraints, 'storage_max_gb', None)
                or getattr(constraints, 'ssd_min_gb', None)
                or getattr(constraints, 'ssd_max_gb', None)
                or getattr(constraints, 'hdd_min_gb', None)
                or getattr(constraints, 'hdd_max_gb', None)
            ))
            or re.search(r'\b(128gb|256gb|500gb|512gb|1tb|2tb|ssd|hdd)\b', query_lower)
        )
        exclude_hdd = bool(constraints is not None and getattr(constraints, 'exclude_hdd', False))
        gaming_blocked = bool(
            constraints is not None and (getattr(constraints, 'exclude_gaming', False) or getattr(constraints, 'gaming_negated', False))
        )

        user_has_heavy_task = bool(_HEAVY_WORDS_RX.search(query_lower))
        gaming_alias_set = set(INTENT_SYNONYMS.get("gaming", []))

        ram_tokens = {'2gb', '4gb', '6gb', '8gb', '12gb', '16gb', '24gb', '32gb', '64gb'}
        storage_tokens = {'128gb', '256gb', '500gb', '512gb', '1tb', '2tb', 'ssd', 'hdd'}
        weak_tokens = {'celeron', 'pentium', 'atom', '2gb', '4gb'}
        generic_product_noise = {'ssd', 'retina'}

        seen_values, tokens = set(), []
        filtered_matched: List[str] = []
        for key in matched:
            if gaming_blocked and (key in gaming_alias_set or 'gaming' in key or 'game' in key):
                continue
            filtered_matched.append(key)
            value = self.dictionary[key]
            if value in seen_values:
                continue
            seen_values.add(value)

            is_product_phrase = key in PRODUCT_IDENTITY_TOKENS
            for tok in value.split():
                if is_product_phrase and tok in generic_product_noise:
                    continue
                if exclude_hdd and tok == 'hdd':
                    continue
                if user_has_ram and tok in ram_tokens:
                    continue
                if user_has_storage and tok in storage_tokens:
                    continue
                if (user_has_heavy_task or user_ram_val >= 8) and tok in weak_tokens:
                    continue
                tokens.append(tok)

        return " ".join(tokens), filtered_matched

    def expansion_terms(self, query: str, constraints=None) -> str:
        terms, _ = self.expand_with_matches(query, constraints=constraints)
        return terms

    def expand(self, query: str, constraints=None) -> str:
        return (query.lower() + " " + self.expansion_terms(query, constraints=constraints)).strip()

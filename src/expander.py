import json
import re
from pathlib import Path

SYNONYM_GROUPS = {
    "murah": ["murah", "terjangkau", "budget", "hemat", "murmer", "ekonomis", "low end", "entry level", "harga bersahabat", "harga miring", "pas kantong"],
    "menengah": ["menengah", "mid range", "midrange", "harga standar"],
    "mahal": ["mahal", "premium", "sultan", "high end", "flagship", "kelas atas"],
    "gaming": ["gaming", "game", "gamer", "ngegame", "main game", "esport", "e-sport", "valorant", "dota", "pubg", "fortnite", "battlefield", "free fire", "mobile legends", "roblox", "minecraft", "genshin", "pes", "fifa", "gta"],
    "edit video": ["edit video", "video edit", "editing video", "ngedit video", "ngedit", "untuk edit", "buat edit", "bisa edit", "laptop edit", "render", "rendering", "animasi", "3d", "premiere", "after effects", "blender", "davinci", "capcut", "youtuber", "konten kreator", "content creator", "streaming", "livestream", "vlog"],
    "desain": ["desain", "design", "edit foto", "editing", "editor", "kreatif", "grafis", "desain grafis", "photoshop", "illustrator", "coreldraw", "figma", "canva", "autocad", "sketchup", "arsitek", "ilustrasi", "lukis"],
    "coding": ["coding", "ngoding", "programmer", "programming", "pemrograman", "developer", "software engineer", "web dev", "data science", "machine learning", "android studio", "vscode", "informatika", "ilmu komputer"],
    "kuliah": ["kuliah", "mahasiswa", "kampus", "skripsi", "anak kuliahan", "anak kuliah", "makalah"],
    "pelajar": ["pelajar", "sekolah", "siswa", "anak sekolah", "belajar", "online class", "daring", "tugas"],
    "kantor": ["kantor", "kantoran", "office", "kerja", "karyawan", "wfh", "dokumen", "ms word", "excel", "presentasi", "admin", "administrasi", "akuntansi"],
    "kencang": ["kencang", "cepat", "performa", "performa tinggi", "bertenaga", "powerful", "ngebut", "gak lemot", "tidak lemot", "anti lemot", "gak ngelag", "anti ngelag", "responsif", "high performance", "spek tinggi", "spek dewa", "spesifikasi tinggi", "gahar"],
    "ringan": ["ringan", "enteng", "tipis", "portabel", "portable", "travel", "mudah dibawa", "praktis", "compact", "kompak", "slim", "mobilitas"],
}

CONTEXTUAL_CHEAP_SPECS = {
    "gaming": "gaming gtx geforce 1050 960m 950m rx 560 i5 ryzen5 8gb ssd fhd",
    "edit video": "ips fhd mx150 radeon i5 ryzen5 8gb 16gb ssd ultrabook notebook",
    "desain": "ips fhd mx150 radeon i5 ryzen5 8gb ssd ultrabook notebook",
    "coding": "i5 ryzen5 i3 8gb ssd fhd notebook ultrabook",
    "kuliah": "notebook i3 ryzen3 celeron pentium 4gb 8gb ssd murah terjangkau entry",
}


class QueryExpander:
    def __init__(self, json_path: Path):
        with open(json_path, 'r', encoding='utf-8') as f:
            base_dict = json.load(f)

        self.dictionary = dict(base_dict)
        
        for canonical, aliases in SYNONYM_GROUPS.items():
            if canonical in self.dictionary:
                spec = self.dictionary[canonical]
                for alias in aliases:
                    self.dictionary.setdefault(alias, spec)

        for uc_key, combo_spec in CONTEXTUAL_CHEAP_SPECS.items():
            for uc_alias in SYNONYM_GROUPS.get(uc_key, [uc_key]):
                for cheap_alias in SYNONYM_GROUPS["murah"]:
                    self.dictionary[f"{uc_alias} {cheap_alias}"] = combo_spec
                    self.dictionary[f"{cheap_alias} {uc_alias}"] = combo_spec
                    self.dictionary[f"{uc_alias} yang {cheap_alias}"] = combo_spec

        for key in list(self.dictionary.keys()):
            words = key.split()
            if len(words) == 2:
                self.dictionary.setdefault(f"{words[1]} {words[0]}", self.dictionary[key])

        self._keys = sorted(self.dictionary.keys(), key=len, reverse=True)
        self._patterns = {
            k: re.compile(r'(?<![a-z0-9])' + re.escape(k.lower()) + r'(?![a-z0-9])')
            for k in self._keys
        }

    def matched_phrases(self, query: str):
        """Daftar frasa kamus yang cocok pada query (tanpa tumpang tindih)."""
        remaining = query.lower()
        matched = []
        for key in self._keys:
            pattern = self._patterns[key]
            if pattern.search(remaining):
                matched.append(key)
                remaining = pattern.sub(' ' * len(key), remaining)
        return matched

    def expansion_terms(self, query: str) -> str:
        """Mengambil term ekspansi dari kamus tanpa menimpa spek eksplisit yang diminta user."""
        query_lower = query.lower()
        user_has_ram = bool(re.search(r'\b(2|4|6|8|12|16|24|32|64)\s*gb\b', query_lower))
        user_has_storage = bool(re.search(r'\b(128gb|256gb|500gb|512gb|1tb|2tb|ssd|hdd)\b', query_lower))
        
        heavy_words = set(SYNONYM_GROUPS["gaming"] + SYNONYM_GROUPS["edit video"] + SYNONYM_GROUPS["desain"] + ["kencang", "cepat", "ngebut", "gahar"])
        user_has_heavy_task = any(w in query_lower for w in heavy_words)

        ram_tokens = {'2gb', '4gb', '6gb', '8gb', '12gb', '16gb', '24gb', '32gb', '64gb'}
        storage_tokens = {'128gb', '256gb', '500gb', '512gb', '1tb', '2tb', 'ssd', 'hdd'}
        low_end_bias = {'celeron', 'pentium', 'i3', 'ryzen3', '2gb', '4gb', 'notebook', 'murah', 'terjangkau', 'entry'}

        seen_values, tokens = set(), []
        for key in self.matched_phrases(query):
            value = self.dictionary[key]
            if value in seen_values:
                continue
            seen_values.add(value)
            
            for tok in value.split():
                if user_has_ram and tok in ram_tokens:
                    continue
                if user_has_storage and tok in storage_tokens:
                    continue
                if (user_has_ram or user_has_storage or user_has_heavy_task) and tok in low_end_bias:
                    continue
                tokens.append(tok)
                
        return " ".join(tokens)

    def expand(self, query: str) -> str:
        return (query.lower() + " " + self.expansion_terms(query)).strip()
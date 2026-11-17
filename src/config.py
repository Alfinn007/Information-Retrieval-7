from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LEGACY_CSV_PATH = BASE_DIR / "data" / "raw" / "laptop_price.csv"
SCRAPED_CSV_PATH = BASE_DIR / "data" / "scraped" / "laptops_new.csv"
DICT_JSON_PATH = BASE_DIR / "data" / "dictionary" / "expansion_dict.json"

EURO_TO_IDR_RATE = 17000

STOPWORDS_ID = {
    "laptop", "yang", "untuk", "buat", "dengan", "cari", "carikan", "dan", "atau",
    "rekomendasi", "kebutuhan", "tolong", "bagus", "cocok", "banget", "sekali",
    "punya", "ada", "kapasitas", "ukuran", "storage", "penyimpanan", "memori", "ram"
}

TECH_NORMALIZATION_RULES = {
    r'\bcore\s*i(\d)\b': r'i\1',
    r'\bryzen\s*(\d)\b': r'ryzen\1',
    r'\b(gtx|rtx)\s*(\d{3,4}(?:ti)?)\b': r'\1 \2',
    r'\b(\d+)\s*gb\b': r'\1gb',
    r'\b(\d+)(?:\.0)?\s*tb\b': r'\1tb',
    r'\bfull\s*hd\b': 'fhd 1920x1080',
    r'\bflash storage\b': 'ssd',
    r'(\d+(?:[.,]\d+)?)\s*(?:inch|inci|")': r'\1 inch'
}

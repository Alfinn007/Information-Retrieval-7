from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LEGACY_CSV_PATH = BASE_DIR / "data" / "raw" / "laptop_price.csv"
SCRAPED_CSV_PATH = BASE_DIR / "data" / "scraped" / "laptops_new.csv"
DICT_JSON_PATH = BASE_DIR / "data" / "dictionary" / "expansion_dict.json"

EURO_TO_IDR_RATE = 17000

STOPWORDS_ID = {
    "laptop", "yang", "untuk", "buat", "dengan", "cari", 
    "rekomendasi", "kebutuhan", "tolong", "bagus", "cocok"
}

TECH_NORMALIZATION_RULES = {
    r'\bcore i(\d)\b': r'i\1',
    r'\bryzen (\d)\b': r'ryzen\1',
    r'\b(\d+)\s*gb\b': r'\1gb',
    r'\bfull hd\b': 'fhd 1920x1080',
    r'\bflash storage\b': 'ssd'
}
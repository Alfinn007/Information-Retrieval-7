"""
Sumber tunggal definisi alias intent dan helper kata negasi
untuk memastikan konsistensi antara parser constraint dan query expander.
"""

INTENT_SYNONYMS = {
    "murah": [
        "murah", "terjangkau", "budget", "hemat", "murmer", "ekonomis",
        "low end", "entry level", "harga bersahabat", "harga miring", "pas kantong"
    ],
    "menengah": ["menengah", "mid range", "midrange", "harga standar"],
    "mahal": ["mahal", "premium", "sultan", "high end", "flagship", "kelas atas"],
    "gaming": [
        "gaming", "game", "gamer", "ngegame", "main game", "esport", "e-sport",
        "valorant", "dota", "pubg", "fortnite", "battlefield", "free fire",
        "mobile legends", "roblox", "minecraft", "genshin", "pes", "fifa", "gta"
    ],
    "edit video": [
        "edit video", "video edit", "editing video", "ngedit video", "ngedit",
        "untuk edit", "buat edit", "bisa edit", "laptop edit", "render",
        "rendering", "animasi", "3d", "premiere", "after effects", "blender",
        "davinci", "capcut", "youtuber", "konten kreator", "content creator",
        "streaming", "livestream", "vlog"
    ],
    "desain": [
        "desain", "design", "edit foto", "editing", "editor", "kreatif",
        "grafis", "desain grafis", "photoshop", "illustrator", "coreldraw",
        "figma", "canva", "autocad", "sketchup", "arsitek", "ilustrasi", "lukis"
    ],
    "coding": [
        "coding", "ngoding", "programmer", "programming", "pemrograman",
        "developer", "software engineer", "web dev", "data science",
        "machine learning", "android studio", "vscode", "informatika",
        "ilmu komputer"
    ],
    "kuliah": [
        "kuliah", "mahasiswa", "kampus", "skripsi", "anak kuliahan",
        "anak kuliah", "makalah"
    ],
    "pelajar": [
        "pelajar", "sekolah", "siswa", "anak sekolah", "belajar",
        "online class", "daring", "tugas"
    ],
    "kantor": [
        "kantor", "kantoran", "office", "kerja", "karyawan", "wfh",
        "dokumen", "ms word", "excel", "presentasi", "admin",
        "administrasi", "akuntansi"
    ],
    "kencang": [
        "kencang", "cepat", "performa", "performa tinggi", "bertenaga",
        "powerful", "ngebut", "gak lemot", "tidak lemot", "anti lemot",
        "gak ngelag", "anti ngelag", "responsif", "high performance",
        "spek tinggi", "spek dewa", "spesifikasi tinggi", "gahar"
    ],
    "ringan": [
        "ringan", "enteng", "tipis", "portabel", "portable", "travel",
        "mudah dibawa", "praktis", "compact", "kompak", "slim", "mobilitas"
    ],
}

# Intent yang memicu asumsi/kebutuhan hardware pada parser
GAMING_ALIASES = INTENT_SYNONYMS["gaming"]
CREATOR_ALIASES = sorted(set(INTENT_SYNONYMS["edit video"] + [
    "autocad", "sketchup", "arsitek", "workstation", "desain grafis",
    "photoshop", "illustrator", "3d"
]))
CODING_ALIASES = INTENT_SYNONYMS["coding"]
LIGHTWEIGHT_ALIASES = INTENT_SYNONYMS["ringan"]
CHEAP_ALIASES = [a for a in INTENT_SYNONYMS["murah"] if a != "budget"]

NEGATION_WORDS = (
    "bukan", "nggak", "enggak", "gak", "ga", "tidak", "tak",
    "tanpa", "jangan", "anti", "non", "no"
)

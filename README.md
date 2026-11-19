# LAPTOPEX — Sistem Rekomendasi Laptop (IR-7)

Sistem *Information Retrieval* berbahasa Indonesia untuk rekomendasi laptop berbasis **Rule-Based Constraint Parsing**, **Dictionary Query Expansion**, dan **TF-IDF Cosine Similarity + Hybrid Ranking**.

## Arsitektur Pipeline IR

1. **Ingestion & Deduplikasi (`src/repository.py`)**: Memuat katalog dari `data/raw/laptop_price.csv` (dan opsional `data/scraped/laptops_new.csv` jika tersedia), melakukan deduplikasi eksak berbasis spesifikasi (1.303 baris mentah → 1.275 dokumen unik), mengonversi harga EUR ke IDR (`1 EUR = Rp17.000`), serta membentuk korpus teks `clean_document`.
2. **Preprocessing (`src/preprocessor.py`, `src/config.py`)**: Normalisasi istilah teknis (`core i5` → `i5`, `16 gb` → `16gb`, `full hd` → `fhd 1920x1080`, `flash storage` → `ssd`, `15.6"` → `15.6 inch`) dan penyaringan stopword bahasa Indonesia.
3. **Constraint Parsing & Negasi (`src/constraints.py`, `src/intents.py`)**:
   - Menangani negasi terlebih dahulu (`tanpa HDD`, `bukan laptop gaming`, `nggak buat gaming`).
   - Mengekstrak batasan terstruktur: rentang/batas harga (`maksimal`, `di bawah`, `di atas`, `sekitar ±20%`), RAM minimum, SSD vs total storage, bobot maksimum (`kg`), ukuran layar (`±0.6 inch`), merek, serta seri produk (`ThinkPad`, `ROG`, `MacBook`, `XPS`, dll.).
   - Menandai asumsi sistem (mis. `gaming`/`edit video`/`coding` → `RAM >= 8GB`) secara transparan dengan `source: "system_assumption"`.
4. **Query Expansion (`src/expander.py`, `data/dictionary/expansion_dict.json`)**: Memetakan bahasa alami Indonesia (*kuliah*, *ngoding*, *murmer*, *2 in 1*, *ringan*, dll.) ke terminologi teknis korpus menggunakan pencocokan frasa *longest-first* dengan batas kata yang menghormati constraint serta negasi pengguna.
5. **TF-IDF & Hybrid Ranking (`src/engine.py`)**:
   - Menggunakan `TfidfVectorizer(sublinear_tf=True)` dengan tokenisasi yang mempertahankan angka desimal (`1.2kg`, `15.6`) dan angka tunggal (`2 in 1`).
   - Menggabungkan vektor kueri `q_vec = base_vec + alpha * exp_vec` (`alpha = 0.5`), menerapkan *hard constraint mask* tanpa relaksasi pada kueri mustahil, lalu menghitung skor peringkat gabungan (*relevansi TF-IDF / quality score*, *affordability*, *lightness*).
6. **Variant Grouping (`src/engine.py`)**: Mengelompokkan varian `(brand, name)` yang sama agar daftar top-N lebih beragam sambil menyertakan konfigurasi lain pada field `variants`.

## Struktur Proyek

```text
.
├── app.py                              # Flask web server & REST API (termasuk config Vercel)
├── main.py                             # Antarmuka CLI interaktif
├── requirements.txt                    # Dependensi Python
├── vercel.json                         # Konfigurasi routing deployment Vercel
├── data/
│   ├── dictionary/
│   │   └── expansion_dict.json         # Kamus ekspansi kueri bahasa Indonesia
│   └── raw/
│       └── laptop_price.csv            # Dataset katalog laptop (1.303 baris mentah)
├── evaluation/
│   ├── annotation_sheet.csv            # Lembar anotasi relevansi blind (tanpa label mode)
│   ├── compute_human_metrics.py        # Kalkulator Precision@5 & nDCG@5 dari anotasi manusia
│   ├── expansion_results.csv           # Hasil top-5 per kueri (no_expansion vs with_expansion)
│   ├── expansion_summary.csv           # Ringkasan kandidat, pelanggaran constraint, & overlap
│   └── run_expansion_experiment.py     # Runner eksperimen A/B 24 kueri evaluasi
├── src/
│   ├── config.py                       # Path konfigurasi, kurs IDR, stopword, & aturan normalisasi
│   ├── constraints.py                  # Parser constraint harga, spesifikasi, negasi, & intent
│   ├── engine.py                       # Engine TF-IDF, hard filtering, ranking, & variant grouping
│   ├── evaluator.py                    # Metrik evaluasi (Precision@K, nDCG@K, top-K overlap)
│   ├── expander.py                     # QueryExpander berbasis kamus + proteksi constraint
│   ├── intents.py                      # Single source of truth alias intent & kata negasi
│   ├── preprocessor.py                 # TextPreprocessor
│   └── repository.py                   # Loader CSV, deduplikasi, & builder korpus
├── tests/
│   ├── test_api_integration.py         # Pengujian integrasi Flask API & zero constraint violations
│   ├── test_constraints.py             # Unit test parser constraint, negasi, & expander
│   ├── test_engine_fixtures.py         # Unit test engine menggunakan fixture sintetis
│   └── test_frontend_js.mjs            # Pengujian logic frontend Vanilla JS via Node VM
└── web/
    ├── app.js                          # Logika UI, fetch API, AbortController, Web Audio retro
    ├── index.html                      # Halaman utama bertema retro Y2K tape-deck
    └── style.css                       # Styling responsif desktop & mobile
```

## Instalasi & Menjalankan

### Prasyarat
- Python 3.10+
- Node.js (opsional, untuk menjalankan tes unit frontend `test_frontend_js.mjs`)

### Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### Menjalankan Web Server (Flask)
```bash
python app.py
```
Akses di browser melalui `http://localhost:5000` (atau port pada variabel lingkungan `PORT`). Aplikasi juga siap di-deploy ke Vercel melalui [vercel.json](vercel.json).

### Menjalankan Mode CLI
```bash
python main.py
```

## Dokumentasi API

### `GET /api/search`
Mencari rekomendasi laptop berdasarkan kueri bahasa alami.
- **Query parameter**:
  - `q` *(wajib)*: String kueri pencarian (tidak boleh kosong).
  - `top` *(opsional, default `30`)*: Jumlah maksimum hasil (`1`–`100`).
- **Contoh respons (`200 OK`)**:
  ```json
  {
    "query": "laptop gaming murah",
    "expanded_query": "gaming gtx geforce 1050 ...",
    "constraints": "GPU Gaming (asumsi sistem), preferensi harga terjangkau",
    "constraints_detail": [...],
    "matched_phrases": ["gaming murah"],
    "relaxed": false,
    "count": 30,
    "total_candidates": 142,
    "catalog_size": 1275,
    "top_limit": 30,
    "price_note": "Harga IDR adalah estimasi dari harga EUR dataset dengan kurs tetap 1 EUR = Rp17.000",
    "results": [...]
  }
  ```

### `GET /api/stats`
Mengembalikan metadata katalog aktif.
- **Contoh respons (`200 OK`)**:
  ```json
  {
    "total_documents": 1275,
    "price_note": "Harga IDR adalah estimasi dari harga EUR dataset dengan kurs tetap 1 EUR = Rp17.000"
  }
  ```

## Pengujian

Jalankan seluruh unit test & integrasi Python:
```bash
pytest -v
```

Jalankan pengujian logic frontend JavaScript:
```bash
node tests/test_frontend_js.mjs
```

## Evaluasi Query Expansion

1. Jalankan eksperimen perbandingan `no_expansion` vs `with_expansion` pada 24 kueri uji:
   ```bash
   python evaluation/run_expansion_experiment.py
   ```
   Output disimpan ke `evaluation/expansion_results.csv`, `evaluation/expansion_summary.csv`, dan lembar penilaian blind `evaluation/annotation_sheet.csv`.
2. Isi kolom `relevance_label` (`0` = tidak relevan, `1` = sebagian sesuai, `2` = sangat sesuai) pada `evaluation/annotation_sheet.csv`, lalu hitung metrik relevansi manusia (`Precision@5` & `nDCG@5`):
   ```bash
   python evaluation/compute_human_metrics.py
   ```

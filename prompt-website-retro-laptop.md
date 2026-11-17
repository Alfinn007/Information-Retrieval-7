Kamu adalah senior front-end engineer sekaligus art director. Buatkan website lengkap untuk proyek "Sistem Rekomendasi Laptop" (Information Retrieval: TF-IDF + Query Expansion + constraint parsing). Gunakan gambar referensi yang kulampirkan sebagai acuan GAYA VISUAL. Tiru gayanya, bukan merek atau logonya. Jangan memakai nama "SOUNDEX". Ganti objek utama di tengah (walkman/kaset transparan) dengan LAPTOP.

==================================================
1. KONSEP & MOOD
==================================================
Gaya: retro-futuristik / Y2K tape-deck / "Walkman product page", dengan nuansa hardware lawas, label teknis, dan grain film.
Kesan: tactile, analog, tipografi raksasa, banyak microtext teknis, tapi tetap bersih dan terbaca.
Nama brand: "LAPTOPEX" (wordmark di tengah header). Tagline: "CARI. BANDINGKAN. PILIH."

==================================================
2. DESIGN TOKENS (perkiraan dari gambar, sesuaikan jika perlu)
==================================================
- --bg-sage: #9CA882 (latar utama hijau sage/olive pudar)
- --ink: #141414 (hitam untuk teks raksasa & microtext)
- --lime: #86D12A (hijau lime asam, untuk tint kaca laptop, aksen, loading)
- --lime-deep: #4C7A12
- --orange: #F2590F (CTA, harga, highlight)
- --paper: #E9E6D8 (stiker/label kertas putih gading)
- --glass: rgba(235,245,225,0.35) (bodi plastik transparan)
- Halaman luar putih bersih; konten utama berada di dalam "frame" kartu besar dengan border-radius 10px dan margin di sekelilingnya, persis seperti gambar.
- Efek grain/noise di seluruh frame: overlay SVG feTurbulence (baseFrequency ~0.8), opacity 0.15-0.22, mix-blend-mode multiply, pointer-events none. Buat sedikit bergerak (animasi steps() tiap ~0.6 detik).
- Tipografi:
  - Display raksasa: font wide + heavy, tinggi dan padat, mirip huruf hitam besar di gambar. Pakai Google Fonts "Anybody" (variable, wdth 150, wght 900) atau fallback "Dela Gothic One".
  - Microtext/label: monospace grotesk kecil, uppercase, letter-spacing 0.04em, ukuran 10-12px. Pakai "Space Mono" atau "JetBrains Mono".
  - Wordmark logo: gaya chrome/outlined graffiti-blackletter. Buat dengan SVG text + stroke + gradient abu-putih metalik, atau font "Rubik Glitch"/"Metal Mania" dengan text-stroke. Harus terlihat seperti logo krom bergerigi.

==================================================
3. LAYOUT HERO (halaman pertama, tinggi penuh viewport)
==================================================
Susun dari atas ke bawah di dalam frame:

A. HEADER (3 kolom, microtext hitam)
- Kiri: dua baris "LAPTOP FINDER / IR-LAPTOP-7" + ikon kecil bergaya glyph "XX/ZZ". Di sebelahnya "● MULAI CARI" dengan titik hitam yang berkedip seperti lampu REC.
- Tengah: wordmark LAPTOPEX (krom) diapit dua ornamen "swoosh/blade" hitam runcing (SVG), menghadap ke luar.
- Kanan: "TYPE 1 NORMAL POSITION" dengan tiga lingkaran kecil di bawahnya, lalu tombol teks "LIHAT HASIL" (anchor ke section hasil).

B. DIVIDER ORNAMEN
- Garis horizontal tipis dengan segmen tebal-tipis putus-putus, diapit ornamen segitiga/blade yang mengecil bertahap di kiri dan kanan (seperti anak panah makin kecil). Di tengah garis ada microtext "CARI, BANDINGKAN, PILIH".

C. MARQUEE TEKS RAKSASA (di belakang laptop)
- Satu baris teks hitam super besar (tinggi ~28-35% tinggi frame), melintang penuh dan terpotong di tepi kiri/kanan frame (overflow hidden), sehingga huruf di pinggir terpotong seperti "SH THE ... LASH TH".
- Isi teks (Bahasa Indonesia): "CARI LAPTOP IMPIANMU — " diulang. Scroll horizontal pelan tak berujung (CSS animation, 30-40 detik per loop).
- Laptop berada DI DEPAN teks sehingga menutupi bagian tengahnya.

D. OBJEK UTAMA: LAPTOP (pengganti kaset)
- Laptop dengan bodi plastik transparan/smoky (gaya Game Boy Color / Y2K clear shell) dengan komponen dalam yang terlihat samar, bertint hijau lime.
- Posisi terbuka sekitar 110 derajat, diputar sekitar 10-14 derajat searah jarum jam dan sedikit perspektif 3D, di tengah frame, ukuran sekitar 55% lebar frame, menimpa teks raksasa.
- Efek: highlight kaca (gradient putih diagonal), tepi bening, bayangan lembut di bawah, sedikit floating (naik-turun 6px, 6 detik, ease-in-out).
- LAYAR LAPTOP adalah input pencarian sungguhan: latar layar hijau lime gelap, ada kursor berkedip, teks placeholder bergaya terminal seperti "ketik: laptop gaming 16gb di bawah 20 juta_". Input ini yang dipakai untuk query.
- Di bodi laptop (area palmrest) tempel stiker kertas --paper miring sedikit, seperti label kaset di gambar, berisi microtext monospace: merek (isi dinamis dengan hasil rank #1 setelah pencarian, default "LAPTOPEX"), "IR-LAPTOP-7", tanggal hari ini, dan skala angka kecil di pinggir.
- Implementasi: bangun laptop murni dengan HTML/CSS/inline SVG (tanpa gambar eksternal) agar single-file berjalan. Sediakan juga slot <img id="laptop-img"> yang diberi komentar jelas, supaya nanti bisa kuganti dengan PNG transparan hasil render 3D laptop clear-shell.

E. BARIS BAWAH (footer hero)
- Kiri: badge hitam kecil "XX1" + dua baris microtext: "IR-LAPTOP-7 · TF-IDF + QUERY EXPANSION" dan "DATASET: 1.303 LAPTOP · 2025".
- Tengah: tab oranye berbentuk trapesium (sisi miring, menempel di tepi bawah frame) bertuliskan "----CARI SEKARANG----". Ini tombol submit.
- Kanan: angka besar monospace "000000000000" yang menunjukkan jumlah hasil (animasi counter naik saat ada hasil).

==================================================
4. SECTION HASIL (di bawah hero, scroll halus ke sini setelah pencarian)
==================================================
Frame sage yang sama, grain yang sama.

- Baris "Filter terdeteksi": chips hitam berbentuk label (isi dari constraints.describe(), pecah per koma). Contoh: "HARGA <= Rp20.000.000", "RAM >= 16GB", "Kategori Gaming / GPU GTX/RTX".
- Baris "Query Expansion": chips outline untuk setiap frasa kamus yang cocok (last_matched). Di bawahnya microtext "EXPANDED QUERY: ..." (expanded_query).
- Jika last_relaxed true, tampilkan banner oranye bergaya strip peringatan: "Tidak ada yang persis cocok, filter dilonggarkan."
- Hasil sebagai kartu bergaya J-card / label kaset: latar --paper, border hitam 2px, sudut sedikit membulat, bayangan keras hitam offset 6px 6px.
  - Kiri: nomor rank sangat besar (font display).
  - Tengah: merek (microtext) + nama laptop (bold), badge kategori (Gaming/Ultrabook/Notebook).
  - Grid spesifikasi 2 kolom, label mono kecil dan nilai: CPU, RAM, STORAGE, GPU, LAYAR, OS, BERAT.
  - Kanan: harga dalam tag oranye format "Rp12.500.000" (titik sebagai pemisah ribuan), dan bar skor relevansi (0-1) berbentuk equalizer/VU meter hijau lime dengan 10-20 segmen.
  - Hover: kartu naik 4px, bayangan membesar, kursor pointer. Klik membuka detail ringkas (accordion).
- Kartu muncul berurutan (stagger) dengan animasi slide-up + fade, 40ms antar kartu.
- Toolbar kecil: urutkan (Relevansi / Harga naik / Harga turun) dan filter cepat berbentuk tombol fisik tape-deck (ikon play/stop/rewind). Pengurutan dilakukan di sisi client.
- Empty state: ilustrasi pita kaset kusut + teks "Maaf, tidak ditemukan laptop yang cocok dengan kata kunci tersebut."
- Loading state: dua "reel" kaset berputar (SVG), teks "MEMUAT... REWINDING".

==================================================
5. INTERAKSI & ANIMASI
==================================================
- Contoh query berbentuk chip yang bisa diklik (isi otomatis ke input): "laptop gaming murah", "edit video 16gb 15 inch", "kuliah ringan di bawah 8 juta", "coding ssd 512gb", "desain grafis 15 juta".
- Tekan Enter atau klik tab oranye untuk mencari.
- Marquee berjalan, laptop floating, titik REC berkedip, kursor layar berkedip, grain bergerak halus.
- Hormati prefers-reduced-motion: matikan semua animasi non-esensial.
- Responsif: desktop 1280+, tablet, dan mobile 375px. Di mobile, teks marquee tetap besar, laptop mengecil dan tetap di tengah, header menjadi 2 baris, kartu hasil menjadi 1 kolom, tab oranye tetap menempel di bawah.
- Aksesibel: kontras teks cukup, input punya label (boleh visually hidden), fokus keyboard terlihat jelas (outline oranye), alt/aria untuk elemen dekoratif (aria-hidden).

==================================================
6. INTEGRASI BACKEND (proyek Python-ku)
==================================================
Backend yang sudah ada (JANGAN ubah logika search-nya): kelas LaptopRecommenderEngine dengan method
engine.search(query, top_n=30, use_expansion=True) yang mengembalikan pandas DataFrame berisi kolom:
id, brand, name, category, display, cpu, ram, storage, gpu, os, weight, price_idr (integer rupiah), score (float), expanded_query.
Atribut tambahan setelah search: engine.last_constraints.describe() (string, mis. "harga <= Rp20.000.000, RAM >= 16GB"), engine.last_matched (list frasa kamus yang cocok), engine.last_relaxed (bool).
Hanya hasil dengan score > 0 yang dianggap relevan.
Inisialisasi yang dipakai di main.py:
  preprocessor = TextPreprocessor(); expander = QueryExpander(DICT_JSON_PATH); repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH); repo.append_scraped_csv(SCRAPED_CSV_PATH); engine = LaptopRecommenderEngine(repo, preprocessor, expander); engine.fit_index()

Buatkan:
1. app.py (Flask + flask-cors) yang menginisialisasi engine SEKALI saat start, dengan endpoint:
   GET /api/search?q=<query>&top=30
   Respons JSON:
   {
     "query": "...",
     "expanded_query": "...",
     "constraints": "harga <= Rp20.000.000, RAM >= 16GB",
     "matched_phrases": ["gaming", "murah"],
     "relaxed": false,
     "count": 12,
     "results": [ { "rank": 1, "brand": "...", "name": "...", "category": "...", "display": "...", "cpu": "...", "ram": "...", "storage": "...", "gpu": "...", "os": "...", "weight": "...", "price_idr": 12500000, "score": 0.4821 } ]
   }
   Tangani query kosong (400), dan filter hanya score > 0.
   Sajikan juga file statis frontend dari folder /static atau /web.
2. Frontend vanilla (tanpa framework, tanpa build tool): web/index.html, web/style.css, web/app.js.
   app.js memakai fetch ke /api/search, merender kartu, format rupiah dengan Intl.NumberFormat('id-ID'), dan punya fallback data mock jika API tidak bisa dihubungi (agar desain bisa dilihat tanpa backend).
3. Struktur folder yang kamu usulkan dan cara menjalankannya (pip install flask flask-cors; python app.py).

==================================================
7. ATURAN OUTPUT
==================================================
- Seluruh teks antarmuka dalam Bahasa Indonesia.
- Berikan KODE LENGKAP dan siap jalan untuk semua file: tidak boleh ada "..." atau "isi sendiri", tidak ada placeholder yang rusak.
- Pakai CSS variables untuk semua token warna dan font. Kode rapi dan diberi komentar singkat.
- Tanpa library eksternal selain Google Fonts. Semua ornamen, laptop, reel, dan noise dibuat dengan SVG/CSS.
- Jangan menyalin teks atau logo persis dari gambar referensi. Ambil gaya, komposisi, palet, dan tipografinya saja.
- Sebelum menulis kode, tulis ringkasan 5-8 poin keputusan desainmu (font, struktur layout, cara membuat laptop transparan). Setelah itu langsung tulis semua file.
- Di akhir, beri daftar kecil "Cara mengganti laptop CSS dengan PNG render sendiri".

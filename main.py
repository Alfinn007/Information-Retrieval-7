import pandas as pd
from src.config import LEGACY_CSV_PATH, SCRAPED_CSV_PATH, DICT_JSON_PATH
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository
from src.expander import QueryExpander
from src.engine import LaptopRecommenderEngine

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def main():
    preprocessor = TextPreprocessor()
    expander = QueryExpander(DICT_JSON_PATH)
    repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH)
    repo.append_scraped_csv(SCRAPED_CSV_PATH)
    engine = LaptopRecommenderEngine(repo, preprocessor, expander)
    engine.fit_index()

    JUMLAH_LIST = 30

    print("=" * 65)
    print("   SISTEM REKOMENDASI LAPTOP - QUERY EXPANSION & TF-IDF")
    print("   Ketik 'exit' untuk keluar dari program")
    print("=" * 65)

    while True:
        user_query = input("\nMasukkan pencarian laptop: ").strip()
        if user_query.lower() in ['exit', 'keluar', 'quit']:
            print("Terima kasih telah menggunakan sistem rekomendasi laptop!")
            break
        if not user_query:
            continue

        hasil = engine.search(user_query, top_n=JUMLAH_LIST, use_expansion=True)
        hasil_relevan = hasil[hasil['score'] > 0].copy() if not hasil.empty else pd.DataFrame()

        print(f"\n[+] Query Pengguna       : {user_query}")
        print(f"[+] Query Asli (Cleaned) : {preprocessor.clean_text(user_query) or '-'}")
        print(f"[+] Filter Terdeteksi    : {engine.last_constraints.describe()}")
        expanded_info = hasil['expanded_query'].iloc[0] if not hasil.empty else "-"
        print(f"[+] Hasil Query Expansion: {expanded_info}")
        if engine.last_relaxed:
            print("[!] Catatan              : Filter dilonggarkan karena tidak ada laptop yang cocok 100%.")

        if hasil_relevan.empty:
            print("\n[!] Maaf, tidak ditemukan laptop yang cocok dengan kata kunci tersebut.")
            continue

        kolom_tampil = ['brand', 'name', 'category', 'cpu', 'ram', 'storage', 'gpu', 'price_idr', 'score']
        tabel_tampil = hasil_relevan[kolom_tampil].copy()
        tabel_tampil.index = range(1, len(tabel_tampil) + 1)
        tabel_tampil.index.name = 'Rank'

        tabel_tampil['price_idr'] = tabel_tampil['price_idr'].apply(lambda x: f"Rp{x:,.0f}".replace(',', '.'))

        print(f"\n--- DAFTAR REKOMENDASI LAPTOP (Menampilkan {len(tabel_tampil)} Hasil Teratas) ---")
        print(tabel_tampil.to_string())

if __name__ == "__main__":
    main()

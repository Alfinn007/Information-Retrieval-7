import os
import socket
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from src.config import LEGACY_CSV_PATH, SCRAPED_CSV_PATH, DICT_JSON_PATH, EURO_TO_IDR_RATE
from src.preprocessor import TextPreprocessor
from src.repository import LaptopRepository
from src.expander import QueryExpander
from src.engine import LaptopRecommenderEngine

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

DEFAULT_TOP_N = 30
MAX_TOP_N = 100

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path='')
CORS(app)


def get_local_ip():
    """Mendapatkan alamat IP lokal komputer untuk akses dari HP / device lain."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# Inisialisasi engine SEKALI saat server start (read-only setelah inisialisasi)
print("[*] Menginisialisasi Sistem Rekomendasi Laptop IR-7...")
preprocessor = TextPreprocessor()
expander = QueryExpander(DICT_JSON_PATH)
repo = LaptopRepository().load_legacy_csv(LEGACY_CSV_PATH)
repo.append_scraped_csv(SCRAPED_CSV_PATH)
engine = LaptopRecommenderEngine(repo, preprocessor, expander)
engine.fit_index()
print("[+] Engine siap menerima request pencarian!")


@app.route('/')
def serve_index():
    """Menyajikan halaman utama frontend."""
    return send_from_directory(str(WEB_DIR), 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Menyajikan file statis (CSS, JS, asset) dari folder web/."""
    return send_from_directory(str(WEB_DIR), path)


@app.route('/api/search', methods=['GET'])
def api_search():
    """
    Endpoint pencarian rekomendasi laptop:
    GET /api/search?q=<query>&top=30 (top: integer 1..100, default 30)
    """
    user_query = request.args.get('q', '').strip()
    if not user_query:
        return jsonify({"error": "Query pencarian tidak boleh kosong."}), 400

    raw_top = request.args.get('top')
    if raw_top is None or raw_top == '':
        top_n = DEFAULT_TOP_N
    else:
        try:
            top_n = int(raw_top)
        except (TypeError, ValueError):
            return jsonify({"error": f"Parameter 'top' harus berupa bilangan bulat (1-{MAX_TOP_N})."}), 400
        if top_n < 1 or top_n > MAX_TOP_N:
            return jsonify({"error": f"Parameter 'top' harus berada di antara 1 dan {MAX_TOP_N}."}), 400

    search_out = engine.search(user_query, top_n=top_n, use_expansion=True)
    df_results = search_out.results

    results_list = []
    if not df_results.empty:
        for rank, (_, row) in enumerate(df_results.iterrows(), start=1):
            results_list.append({
                "rank": rank,
                "id": str(row.get('id', '')),
                "brand": str(row.get('brand', '')),
                "name": str(row.get('name', '')),
                "category": str(row.get('category', '')),
                "display": str(row.get('display', '')),
                "cpu": str(row.get('cpu', '')),
                "ram": str(row.get('ram', '')),
                "storage": str(row.get('storage', '')),
                "gpu": str(row.get('gpu', '')),
                "os": str(row.get('os', '')),
                "weight": str(row.get('weight', '')),
                "price_idr": int(row.get('price_idr', 0)),
                "score": float(row.get('score', 0.0)),
                "match_reasons": list(row.get('match_reasons', []) or []),
                "variants": list(row.get('variants', []) or []),
            })

    response_data = {
        "query": user_query,
        "expanded_query": search_out.expanded_query,
        "constraints": search_out.constraints.describe(),
        "constraints_detail": search_out.constraints.to_structured_list(),
        "matched_phrases": search_out.matched_phrases,
        "relaxed": bool(search_out.relaxed),
        "count": len(results_list),
        "total_candidates": int(search_out.total_candidates),
        "top_limit": top_n,
        "price_note": f"Harga IDR adalah estimasi dari harga EUR dataset dengan kurs tetap 1 EUR = Rp{EURO_TO_IDR_RATE:,.0f}".replace(',', '.'),
        "results": results_list,
    }

    return jsonify(response_data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    local_ip = get_local_ip()
    print("=" * 65)
    print("   SISTEM REKOMENDASI LAPTOPEX SIAP DIAKSES!")
    print(f"   [+] Akses dari Komputer ini : http://localhost:{port}")
    print(f"   [+] Akses dari HP / Device  : http://{local_ip}:{port}")
    print("   (Pastikan HP terhubung ke jaringan Wi-Fi yang sama)")
    print("=" * 65)
    app.run(host='0.0.0.0', port=port, debug=False)

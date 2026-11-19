import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.constraints import parse_constraints
from src.config import DICT_JSON_PATH
from src.expander import QueryExpander


def test_price_formats_equivalent():
    queries = [
        "laptop maksimal 8 juta",
        "laptop maks 8jt",
        "laptop budget 8 juta",
        "laptop maksimal 8000000",
        "laptop maksimal Rp8.000.000",
    ]
    for q in queries:
        c, _ = parse_constraints(q)
        assert c.price_max == 8_000_000, f"Gagal pada: {q}"
        assert c.price_max_inclusive is True
        assert c.prefer_cheap is False, f"'budget' / 'maksimal' tidak boleh mengaktifkan prefer_cheap: {q}"


def test_price_decimal_and_range():
    c1, _ = parse_constraints("laptop 7,5 juta")
    c2, _ = parse_constraints("laptop 7.5 juta")
    assert c1.price_min == c2.price_min == 6_000_000
    assert c1.price_max == c2.price_max == 9_000_000
    assert c1.price_around_target == 7_500_000

    r1, _ = parse_constraints("laptop 5–8 juta")
    r2, _ = parse_constraints("laptop 5 sampai 8 juta")
    assert r1.price_min == r2.price_min == 5_000_000
    assert r1.price_max == r2.price_max == 8_000_000


def test_price_operators_and_cheapest():
    c_under, _ = parse_constraints("laptop di bawah 8 juta")
    assert c_under.price_max == 8_000_000 and c_under.price_max_inclusive is False

    c_above, _ = parse_constraints("laptop di atas 8 juta")
    assert c_above.price_min == 8_000_000 and c_above.price_min_inclusive is False

    c_min, _ = parse_constraints("laptop 8 juta ke atas")
    assert c_min.price_min == 8_000_000 and c_min.price_min_inclusive is True

    c_cheapest, rem = parse_constraints("yang paling murah di bawah 8 juta")
    assert c_cheapest.price_max == 8_000_000
    assert c_cheapest.price_max_inclusive is False
    assert c_cheapest.sort_cheapest_explicit is True
    assert "murah" not in rem


def test_storage_does_not_leak_into_ram():
    c1, _ = parse_constraints("SSD 512 GB")
    assert c1.ssd_min_gb == 512 and c1.ram_min is None

    c2, _ = parse_constraints("512GB SSD")
    assert c2.ssd_min_gb == 512 and c2.ram_min is None

    c3, _ = parse_constraints("RAM 16GB SSD 512GB")
    assert c3.ram_min == 16 and c3.ssd_min_gb == 512

    c4, _ = parse_constraints("SSD 64GB")
    assert c4.ssd_min_gb == 64 and c4.ram_min is None


def test_negation_and_expander_alignment():
    expander = QueryExpander(DICT_JSON_PATH)

    c1, rem1 = parse_constraints("bukan laptop gaming")
    assert c1.exclude_gaming is True
    assert c1.require_gaming_gpu is False
    terms1, matched1 = expander.expand_with_matches(rem1, constraints=c1)
    assert "gaming" not in matched1 and "gtx" not in terms1

    c2, rem2 = parse_constraints("buat kuliah, nggak buat gaming")
    assert c2.gaming_negated is True
    assert c2.exclude_gaming is False
    assert c2.require_gaming_gpu is False
    terms2, matched2 = expander.expand_with_matches(rem2, constraints=c2)
    assert "kuliah" in matched2
    assert "gaming" not in matched2 and "gtx" not in terms2

    c3, rem3 = parse_constraints("Nggak buat gaming, tapi buat edit video")
    assert c3.gaming_negated is True
    assert c3.require_gaming_gpu is False
    assert c3.require_creator_spec is True
    terms3, matched3 = expander.expand_with_matches(rem3, constraints=c3)
    assert "edit video" in matched3 and "gaming" not in matched3

    c4, rem4 = parse_constraints("tanpa HDD")
    assert c4.exclude_hdd is True
    assert "hdd" not in rem4

    c_minecraft, _ = parse_constraints("laptop buat main minecraft")
    c_roblox, _ = parse_constraints("laptop untuk roblox")
    assert c_minecraft.require_gaming_gpu is True
    assert c_roblox.require_gaming_gpu is True


def test_system_assumption_metadata():
    c, _ = parse_constraints("ngoding budget 8 juta")
    assert c.ram_min == 8
    assert c.ram_source == "system_assumption"
    structured = c.to_structured_list()
    ram_item = next(item for item in structured if item["key"] == "ram_min")
    assert ram_item["source"] == "system_assumption"
    assert "asumsi sistem" in ram_item["label"]


def test_expander_word_boundary_no_substring_leak():
    expander = QueryExpander(DICT_JSON_PATH)

    terms_spec, matched_spec = expander.expand_with_matches("spesifikasi murah")
    assert "murah" in matched_spec
    for tok in ("celeron", "pentium", "4gb"):
        assert tok in terms_spec.split(), f"Token {tok} tidak boleh terhapus oleh substring 'pes' di 'spesifikasi'"

    terms_pes, matched_pes = expander.expand_with_matches("laptop main pes, tapi murah")
    assert "pes" in matched_pes and "murah" in matched_pes
    for tok in ("celeron", "pentium", "4gb"):
        assert tok not in terms_pes.split(), f"Query gaming 'pes' harus tetap membuang token lemah {tok}"


def test_paket1_multi_clause_and_price_variants():
    for q in (
        "minimal 5 juta dan maksimal 8 juta",
        "maksimal 8 juta dan minimal 5 juta",
        "antara 5 dan 8 juta",
    ):
        c, _ = parse_constraints(q)
        assert c.price_min == 5_000_000 and c.price_max == 8_000_000
        assert c.price_min_inclusive is True and c.price_max_inclusive is True
        assert c.price_around_target is None

    c_contra, _ = parse_constraints("minimal 15 juta dan maksimal 8 juta")
    assert c_contra.price_min == 15_000_000 and c_contra.price_max == 8_000_000

    for q in (
        "maksimal Rp8 juta",
        "budget Rp 8 juta",
        "budget saya 8 juta",
        "maksimal 8.000.000",
        "≤ 8 juta",
        "laptop harga maksimal 8 juta",
        "maksimal 8 juta dong",
    ):
        c, _ = parse_constraints(q)
        assert c.price_max == 8_000_000, f"Gagal pada: {q}"
        assert c.price_max_inclusive is True
        assert c.price_around_target is None, f"Tidak boleh jadi around pada: {q}"

    c_kebawah, _ = parse_constraints("8,5 juta ke bawah")
    assert c_kebawah.price_max == 8_500_000 and c_kebawah.price_max_inclusive is True


def test_paket1_component_binding_and_operator_directions():
    c_ram_min, _ = parse_constraints("minimal RAM 16 GB")
    assert c_ram_min.ram_min == 16 and c_ram_min.ram_max is None

    c_ram_max, _ = parse_constraints("RAM maksimal 8 GB")
    assert c_ram_max.ram_max == 8 and c_ram_max.ram_min is None

    c_ram_128, _ = parse_constraints("RAM 128GB")
    assert c_ram_128.ram_min == 128 and c_ram_128.storage_min_gb is None

    c_ssd_half, _ = parse_constraints("SSD 0,5 TB")
    assert c_ssd_half.ssd_min_gb == 500 and c_ssd_half.ssd_max_gb is None

    c_ssd_max, _ = parse_constraints("SSD maksimal 256 GB")
    assert c_ssd_max.ssd_max_gb == 256 and c_ssd_max.ssd_min_gb is None and c_ssd_max.storage_min_gb is None

    c_hdd, _ = parse_constraints("HDD 1TB")
    assert c_hdd.hdd_min_gb == 1000 and c_hdd.storage_min_gb is None

    c_w_min, _ = parse_constraints("Lenovo berat minimal 2 kg")
    assert c_w_min.weight_min_kg == 2.0 and c_w_min.weight_max_kg is None

    c_scr_min, _ = parse_constraints("layar minimal 15 inci")
    assert c_scr_min.screen_min_inch == 15.0 and c_scr_min.screen_inch is None


def test_paket2_explicit_specs_and_touchscreen():
    c_w11, _ = parse_constraints("Windows 11")
    assert c_w11.required_os == "windows 11"

    c_dw11, _ = parse_constraints("laptop dengan Windows 11")
    assert c_dw11.required_os == "windows 11"

    c_lin, _ = parse_constraints("Linux")
    assert c_lin.required_os == "linux"

    c_rtx, _ = parse_constraints("NVIDIA RTX 4060")
    assert c_rtx.required_gpu == "rtx 4060"

    c_i5, _ = parse_constraints("Intel Core i5")
    assert c_i5.required_cpu == "intel core i5"

    c_m3, rem_m3 = parse_constraints("MacBook M3")
    assert c_m3.required_cpu == "apple m3"
    assert "macbook" in rem_m3

    c_wt, _ = parse_constraints("wajib touchscreen")
    assert c_wt.require_touchscreen is True and c_wt.exclude_touchscreen is False

    c_nt, rem_nt = parse_constraints("tanpa touchscreen")
    assert c_nt.exclude_touchscreen is True and c_nt.require_touchscreen is False
    assert "touchscreen" not in rem_nt

    c_2in1, _ = parse_constraints("laptop 2 in 1 touch screen")
    assert c_2in1.require_convertible is True and c_2in1.require_touchscreen is True

    c_as, _ = parse_constraints("laptop buat android studio")
    assert c_as.required_os is None and c_as.ram_min == 8

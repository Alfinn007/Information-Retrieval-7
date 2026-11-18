import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.intents import (
    CHEAP_ALIASES,
    CODING_ALIASES,
    CREATOR_ALIASES,
    GAMING_ALIASES,
    LIGHTWEIGHT_ALIASES,
    NEGATION_WORDS,
)

VALID_RAM_GB = {2, 4, 6, 8, 12, 16, 24, 32, 64}
SCREEN_TOLERANCE = 0.6
AROUND_RATIO = 0.2

_UPPER_STRICT = r'(?:di\s?bawah|under|kurang\s+dari|<(?!=))'
_UPPER_INCLUSIVE = r'(?:maksimal|maksimum|maks|max|budget|anggaran|tidak\s+lebih\s+dari|paling\s+mahal|<=)'
_UPPER = rf'(?:{_UPPER_STRICT}|{_UPPER_INCLUSIVE})'

_LOWER_STRICT = r'(?:di\s?atas|above|lebih\s+dari|>(?!=))'
_LOWER_INCLUSIVE = r'(?:minimal|minimum|min|>=)'
_LOWER = rf'(?:{_LOWER_STRICT}|{_LOWER_INCLUSIVE})'

_AROUND = r'(?:sekitar|kisaran|around|harga|di\s+harga|~)'
_SEP = r'(?:-|–|—|sampai|sd|s/d|hingga|to)'


def _compile_phrase_rx(phrases: List[str]) -> re.Pattern:
    ordered = sorted(set(phrases), key=len, reverse=True)
    alt = "|".join(re.escape(p) for p in ordered)
    return re.compile(rf'(?<![a-z0-9])(?:{alt})(?![a-z0-9])')


_CHEAP_INTENT = _compile_phrase_rx(CHEAP_ALIASES)
_GAMING_INTENT = _compile_phrase_rx(GAMING_ALIASES)
_CREATOR_INTENT = _compile_phrase_rx(CREATOR_ALIASES)
_CODING_INTENT = _compile_phrase_rx(CODING_ALIASES)
_LIGHTWEIGHT_INTENT = _compile_phrase_rx(LIGHTWEIGHT_ALIASES)
_EXPLICIT_CHEAPEST = re.compile(r'\b(?:yang\s+)?(?:paling\s+murah|termurah)\b')

_NEG_ALT = "|".join(NEGATION_WORDS)
_GAMING_ALT = "|".join(re.escape(p) for p in sorted(set(GAMING_ALIASES), key=len, reverse=True))
_CREATOR_ALT = "|".join(re.escape(p) for p in sorted(set(CREATOR_ALIASES), key=len, reverse=True))
_CODING_ALT = "|".join(re.escape(p) for p in sorted(set(CODING_ALIASES), key=len, reverse=True))
_LIGHT_ALT = "|".join(re.escape(p) for p in sorted(set(LIGHTWEIGHT_ALIASES), key=len, reverse=True))

_NEG_HDD_RX = re.compile(r'\b(?:tanpa|no|non|bukan|jangan)\s+(?:pakai\s+|ada\s+)?(?:hdd|harddisk|hard\s*disk)\b')
_NEG_GAMING_RX = re.compile(
    rf'\b(?P<neg>{_NEG_ALT})\s+(?:usah\s+|perlu\s+|mau\s+)?(?:untuk\s+|buat\s+)?(?P<lap>laptop\s+)?(?:{_GAMING_ALT})\b'
)
_NEG_CREATOR_RX = re.compile(
    rf'\b(?:{_NEG_ALT})\s+(?:usah\s+|perlu\s+)?(?:untuk\s+|buat\s+)?(?:{_CREATOR_ALT})\b'
)
_NEG_CODING_RX = re.compile(
    rf'\b(?:{_NEG_ALT})\s+(?:usah\s+|perlu\s+)?(?:untuk\s+|buat\s+)?(?:{_CODING_ALT})\b'
)
_NEG_LIGHT_RX = re.compile(
    rf'\b(?:{_NEG_ALT})\s+(?:usah\s+|perlu\s+)?(?:{_LIGHT_ALT})\b'
)

_RANGE_JUTA = re.compile(
    rf'(?P<a>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)?\s*{_SEP}\s*(?P<b>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)\b'
)
_RANGE_PLAIN = re.compile(
    rf'(?:rp\.?\s*)?(?P<a>\d{{1,3}}(?:\.\d{{3}})+|\d{{6,9}})\s*{_SEP}\s*(?:rp\.?\s*)?(?P<b>\d{{1,3}}(?:\.\d{{3}})+|\d{{6,9}})\b'
)
_MONEY = re.compile(
    r'(?:rp\.?\s*(?P<full>\d{1,3}(?:\.\d{3})+|\d{6,9})\b'
    r'|(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>jutaan|juta|jtan|jt)\b'
    r'|(?P<plain>\b\d{6,9}\b))'
)

_SSD_A = re.compile(
    r'\b(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s+)?'
    r'ssd\s*(?:(?P<op2>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s+)?'
    r'(?P<v>\d+(?:\.\d+)?)\s*(?P<u>tb|gb)\b'
)
_SSD_B = re.compile(
    r'\b(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s+)?'
    r'(?P<v>\d+(?:\.\d+)?)\s*(?P<u>tb|gb)\s*ssd\b'
)

_STORAGE_TB = re.compile(
    r'\b(?:(?:storage|penyimpanan|kapasitas|memori)\s*)?'
    r'(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s+)?'
    r'(?P<v>[12])(?:\.0)?\s*tb\b'
)
_STORAGE_GB = re.compile(
    r'\b(?:(?:storage|penyimpanan|kapasitas|memori)\s*)?'
    r'(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s+)?'
    r'(?P<v>128|256|500|512|1000|1024)\s*gb\b'
)

_WEIGHT = re.compile(
    r'(?:berat\s*(?P<op1>maksimal|maksimum|maks|max|di\s?bawah|kurang\s+dari|<=?)?\s*|'
    r'(?P<op2>maksimal|maksimum|maks|max|di\s?bawah|kurang\s+dari|<=?)\s+)'
    r'(?P<v>\d+(?:[.,]\d+)?)\s*kg\b'
    r'|(?P<v2>\d+(?:[.,]\d+)?)\s*kg\b'
)

_RAM_A = re.compile(
    r'\bram\s*(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s*)?(?P<v>\d{1,2})\s*(?:gb|g)?\b'
)
_RAM_B = re.compile(
    r'\b(?:(?P<op>minimal|minimum|min|di\s?atas|lebih\s+dari|>=?)\s*)?(?P<v>\d{1,2})\s*(?:gb|g)\s*(?:ram)?\b'
)

_SCREEN = re.compile(r'(?:layar\s*)?\b(?P<v>\d{2}(?:[.,]\d)?)\s*(?:inch|inci|in\b|")')


def _fmt_idr(val: int) -> str:
    return f"Rp{val:,.0f}".replace(",", ".")


def _to_float(s: str) -> float:
    return float(s.replace(',', '.'))


def _parse_money_token(raw: str) -> int:
    return int(raw.replace('.', ''))


def _money_value(m: re.Match) -> int:
    if m.group('full'):
        return _parse_money_token(m.group('full'))
    if m.group('plain'):
        return int(m.group('plain'))
    return int(round(_to_float(m.group('num')) * 1_000_000))


def _is_strict_op(op: Optional[str]) -> bool:
    if not op:
        return False
    op_l = op.lower().strip()
    return bool(re.match(r'^(?:di\s?atas|lebih\s+dari|di\s?bawah|kurang\s+dari|under|above|[<>])$', op_l))


def _cut(text: str, spans: List[Tuple[int, int]]) -> str:
    chars = list(text)
    for s, e in spans:
        for i in range(max(0, s), min(len(chars), e)):
            chars[i] = ' '
    return re.sub(r'\s+', ' ', ''.join(chars)).strip()


@dataclass
class Constraints:
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    price_min_inclusive: bool = True
    price_max_inclusive: bool = True
    price_around_target: Optional[int] = None

    ram_min: Optional[int] = None
    ram_min_inclusive: bool = True
    ram_source: str = "user"
    ram_reason: Optional[str] = None

    storage_min_gb: Optional[int] = None
    storage_min_inclusive: bool = True
    ssd_min_gb: Optional[int] = None
    ssd_min_inclusive: bool = True
    exclude_hdd: bool = False

    weight_max_kg: Optional[float] = None
    weight_max_inclusive: bool = True

    screen_inch: Optional[float] = None

    require_gaming_gpu: bool = False
    exclude_gaming: bool = False
    gaming_negated: bool = False
    require_creator_spec: bool = False

    prefer_cheap: bool = False
    sort_cheapest_explicit: bool = False
    prefer_lightweight: bool = False

    required_brand: Optional[str] = None
    required_family: Optional[str] = None

    applied_filters: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def sort_cheapest(self) -> bool:
        return self.prefer_cheap or self.sort_cheapest_explicit

    @property
    def is_empty(self) -> bool:
        return (
            self.price_min is None
            and self.price_max is None
            and self.ram_min is None
            and self.storage_min_gb is None
            and self.ssd_min_gb is None
            and not self.exclude_hdd
            and self.weight_max_kg is None
            and self.screen_inch is None
            and not self.require_gaming_gpu
            and not self.exclude_gaming
            and not self.require_creator_spec
            and not self.prefer_cheap
            and not self.sort_cheapest_explicit
            and not self.prefer_lightweight
            and self.required_brand is None
            and self.required_family is None
        )

    def build_applied_filters(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        if self.price_min is not None and self.price_max is not None:
            if self.price_around_target is not None:
                label = f"harga {_fmt_idr(self.price_min)} - {_fmt_idr(self.price_max)} (sekitar {_fmt_idr(self.price_around_target)})"
            else:
                label = f"harga {_fmt_idr(self.price_min)} - {_fmt_idr(self.price_max)}"
            items.append({"key": "price_range", "label": label, "source": "user", "kind": "hard"})
        elif self.price_min is not None:
            op = ">=" if self.price_min_inclusive else ">"
            items.append({"key": "price_min", "label": f"harga {op} {_fmt_idr(self.price_min)}", "source": "user", "kind": "hard"})
        elif self.price_max is not None:
            op = "<=" if self.price_max_inclusive else "<"
            items.append({"key": "price_max", "label": f"harga {op} {_fmt_idr(self.price_max)}", "source": "user", "kind": "hard"})

        if self.ram_min is not None:
            op = ">=" if self.ram_min_inclusive else ">"
            if self.ram_source == "system_assumption":
                label = f"RAM {op} {self.ram_min}GB (asumsi sistem: {self.ram_reason})"
            else:
                label = f"RAM {op} {self.ram_min}GB"
            items.append({"key": "ram_min", "label": label, "source": self.ram_source, "kind": "hard"})

        if self.ssd_min_gb is not None:
            op = ">=" if self.ssd_min_inclusive else ">"
            lbl = f"{self.ssd_min_gb // 1000}TB" if self.ssd_min_gb >= 1000 and self.ssd_min_gb % 1000 == 0 else f"{self.ssd_min_gb}GB"
            items.append({"key": "ssd_min_gb", "label": f"SSD {op} {lbl}", "source": "user", "kind": "hard"})

        if self.storage_min_gb is not None:
            op = ">=" if self.storage_min_inclusive else ">"
            lbl = f"{self.storage_min_gb // 1000}TB" if self.storage_min_gb >= 1000 and self.storage_min_gb % 1000 == 0 else f"{self.storage_min_gb}GB"
            items.append({"key": "storage_min_gb", "label": f"Storage {op} {lbl}", "source": "user", "kind": "hard"})

        if self.exclude_hdd:
            items.append({"key": "exclude_hdd", "label": "tanpa HDD", "source": "user", "kind": "hard"})

        if self.weight_max_kg is not None:
            op = "<=" if self.weight_max_inclusive else "<"
            items.append({"key": "weight_max_kg", "label": f"berat {op} {self.weight_max_kg:g} kg", "source": "user", "kind": "hard"})

        if self.screen_inch is not None:
            items.append({"key": "screen_inch", "label": f"layar ~{self.screen_inch:g} inch", "source": "user", "kind": "hard"})

        if self.required_brand:
            items.append({"key": "brand", "label": f"merek {self.required_brand}", "source": "user", "kind": "hard"})
        if self.required_family:
            items.append({"key": "family", "label": f"seri {self.required_family}", "source": "user", "kind": "hard"})

        if self.exclude_gaming:
            items.append({"key": "exclude_gaming", "label": "bukan kategori Gaming", "source": "user", "kind": "hard"})
        elif self.gaming_negated:
            items.append({"key": "gaming_negated", "label": "tanpa kebutuhan gaming", "source": "user", "kind": "preference"})

        if self.require_gaming_gpu:
            items.append({"key": "require_gaming_gpu", "label": "GPU Gaming (asumsi sistem)", "source": "system_assumption", "kind": "hard"})
        elif self.require_creator_spec:
            items.append({"key": "require_creator_spec", "label": "GPU Dedicated (asumsi sistem)", "source": "system_assumption", "kind": "hard"})

        if self.sort_cheapest_explicit:
            items.append({"key": "sort_cheapest_explicit", "label": "urutan paling murah", "source": "user", "kind": "preference"})
        elif self.prefer_cheap:
            items.append({"key": "prefer_cheap", "label": "preferensi harga terjangkau", "source": "user", "kind": "preference"})

        if self.prefer_lightweight:
            items.append({"key": "prefer_lightweight", "label": "preferensi bobot ringan", "source": "user", "kind": "preference"})

        self.applied_filters = items
        return items

    def to_structured_list(self) -> List[Dict[str, Any]]:
        if not self.applied_filters:
            return self.build_applied_filters()
        return list(self.applied_filters)

    def describe(self) -> str:
        items = self.to_structured_list()
        if not items:
            return "Tidak ada filter khusus"
        return ", ".join(item["label"] for item in items)


def _strip_negated_clauses(text: str, c: Constraints) -> str:
    """Deteksi dan potong frasa yang disangkal sebelum rule intent & expander dijalankan."""
    spans: List[Tuple[int, int]] = []

    for m in _NEG_HDD_RX.finditer(text):
        c.exclude_hdd = True
        spans.append(m.span())

    for m in _NEG_GAMING_RX.finditer(text):
        neg_word = (m.group('neg') or '').lower()
        has_laptop = bool(m.group('lap'))
        if neg_word in ('bukan', 'anti', 'non') or has_laptop:
            c.exclude_gaming = True
        else:
            c.gaming_negated = True
        spans.append(m.span())

    for rx in (_NEG_CREATOR_RX, _NEG_CODING_RX, _NEG_LIGHT_RX):
        for m in rx.finditer(text):
            spans.append(m.span())

    return _cut(text, spans) if spans else text


def parse_constraints(query: str) -> Tuple[Constraints, str]:
    text = re.sub(r'\s+', ' ', query.lower()).strip()
    c = Constraints()

    # 1. Negasi diproses terlebih dahulu sebelum intent & expander
    text = _strip_negated_clauses(text, c)
    spans: List[Tuple[int, int]] = []

    # 2. Harga (rentang atau nominal tunggal)
    m_rj = _RANGE_JUTA.search(text)
    m_rp = _RANGE_PLAIN.search(text) if not m_rj else None
    if m_rj:
        v1 = int(round(_to_float(m_rj.group('a')) * 1_000_000))
        v2 = int(round(_to_float(m_rj.group('b')) * 1_000_000))
        c.price_min, c.price_max = min(v1, v2), max(v1, v2)
        start, end = m_rj.span()
        prefix = text[max(0, start - 25):start]
        cue = re.search(r'(?:budget|anggaran|harga|kisaran|sekitar)\s*$', prefix)
        if cue:
            start -= len(cue.group(0))
        spans.append((start, end))
    elif m_rp:
        v1 = _parse_money_token(m_rp.group('a'))
        v2 = _parse_money_token(m_rp.group('b'))
        c.price_min, c.price_max = min(v1, v2), max(v1, v2)
        start, end = m_rp.span()
        prefix = text[max(0, start - 25):start]
        cue = re.search(r'(?:budget|anggaran|harga|kisaran|sekitar)\s*$', prefix)
        if cue:
            start -= len(cue.group(0))
        spans.append((start, end))
    else:
        m = _MONEY.search(text)
        if m:
            value = _money_value(m)
            start, end = m.start(), m.end()
            prefix = text[max(0, start - 28):start]
            suffix = text[end:end + 20]

            suf_u_strict = re.match(r'\s*(?:ke\s?bawah)\b', suffix)
            suf_u_incl = re.match(r'\s*(?:maks(?:imal|imum)?|max)\b', suffix)
            suf_l_incl = re.match(r'\s*(?:ke\s?atas|minimal|minimum|min)\b', suffix)

            cue_u_strict = re.search(_UPPER_STRICT + r'\s*$', prefix)
            cue_u_incl = re.search(_UPPER_INCLUSIVE + r'\s*$', prefix)
            cue_l_strict = re.search(_LOWER_STRICT + r'\s*$', prefix)
            cue_l_incl = re.search(_LOWER_INCLUSIVE + r'\s*$', prefix)
            cue_a = re.search(_AROUND + r'\s*$', prefix)

            if cue_u_strict or suf_u_strict:
                c.price_max = value
                c.price_max_inclusive = False
                if cue_u_strict:
                    start -= len(cue_u_strict.group(0))
                if suf_u_strict:
                    end += len(suf_u_strict.group(0))
            elif cue_u_incl or suf_u_incl:
                c.price_max = value
                c.price_max_inclusive = True
                if cue_u_incl:
                    start -= len(cue_u_incl.group(0))
                if suf_u_incl:
                    end += len(suf_u_incl.group(0))
            elif cue_l_strict:
                c.price_min = value
                c.price_min_inclusive = False
                start -= len(cue_l_strict.group(0))
            elif cue_l_incl or suf_l_incl:
                c.price_min = value
                c.price_min_inclusive = True
                if cue_l_incl:
                    start -= len(cue_l_incl.group(0))
                if suf_l_incl:
                    end += len(suf_l_incl.group(0))
            else:
                c.price_around_target = value
                c.price_min = int(round(value * (1 - AROUND_RATIO)))
                c.price_max = int(round(value * (1 + AROUND_RATIO)))
                if cue_a:
                    start -= len(cue_a.group(0))
            spans.append((start, end))

    text_no_price = _cut(text, spans)
    spans = []

    # 3. SSD & Storage lebih dulu supaya angka kapasitas tidak terbaca sebagai RAM
    for rx in (_SSD_A, _SSD_B):
        m = rx.search(text_no_price)
        if m:
            val = float(m.group('v'))
            gb = int(round(val * 1000)) if m.group('u') == 'tb' else int(round(val))
            c.ssd_min_gb = gb
            op = m.group('op') or (m.groupdict().get('op2') if 'op2' in m.groupdict() else None)
            c.ssd_min_inclusive = not _is_strict_op(op)
            spans.append(m.span())
            break

    text_no_ssd = _cut(text_no_price, spans)
    spans = []

    m_tb = _STORAGE_TB.search(text_no_ssd)
    m_gb = _STORAGE_GB.search(text_no_ssd)
    if m_tb:
        c.storage_min_gb = int(m_tb.group('v')) * 1000
        c.storage_min_inclusive = not _is_strict_op(m_tb.group('op'))
        spans.append(m_tb.span())
    elif m_gb:
        c.storage_min_gb = int(m_gb.group('v'))
        c.storage_min_inclusive = not _is_strict_op(m_gb.group('op'))
        spans.append(m_gb.span())

    text_no_storage = _cut(text_no_ssd, spans)
    spans = []

    # 4. Berat (kg)
    m_w = _WEIGHT.search(text_no_storage)
    if m_w:
        v_str = m_w.group('v') or m_w.group('v2')
        w_val = _to_float(v_str)
        if 0.3 <= w_val <= 10.0:
            c.weight_max_kg = w_val
            op = m_w.group('op1') or m_w.group('op2')
            c.weight_max_inclusive = not _is_strict_op(op)
            spans.append(m_w.span())

    # 5. RAM
    for rx in (_RAM_A, _RAM_B):
        m = rx.search(text_no_storage)
        if m and int(m.group('v')) in VALID_RAM_GB:
            c.ram_min = int(m.group('v'))
            c.ram_min_inclusive = not _is_strict_op(m.group('op'))
            c.ram_source = "user"
            spans.append(m.span())
            break

    # 6. Layar
    m_scr = _SCREEN.search(text_no_storage)
    if m_scr and 10 <= _to_float(m_scr.group('v')) <= 18.5:
        c.screen_inch = _to_float(m_scr.group('v'))
        spans.append(m_scr.span())

    clean_remaining = _cut(text_no_storage, spans)

    # 7. Preferensi paling murah vs preferensi murah/hemat
    if _EXPLICIT_CHEAPEST.search(clean_remaining):
        c.sort_cheapest_explicit = True
        clean_remaining = _EXPLICIT_CHEAPEST.sub(' ', clean_remaining)
        clean_remaining = re.sub(r'\s+', ' ', clean_remaining).strip()
    elif _CHEAP_INTENT.search(clean_remaining) or re.search(r'\bbudget\b', clean_remaining):
        c.prefer_cheap = True

    if _LIGHTWEIGHT_INTENT.search(clean_remaining) and c.weight_max_kg is None:
        c.prefer_lightweight = True

    # 8. Intent kebutuhan & asumsi sistem
    if _GAMING_INTENT.search(clean_remaining) and not c.exclude_gaming:
        c.require_gaming_gpu = True
        if c.ram_min is None:
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "gaming"
    elif _CREATOR_INTENT.search(clean_remaining):
        c.require_creator_spec = True
        if c.ram_min is None:
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "edit video/desain"
    elif _CODING_INTENT.search(clean_remaining):
        if c.ram_min is None:
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "coding/ngoding"

    c.build_applied_filters()
    return c, clean_remaining

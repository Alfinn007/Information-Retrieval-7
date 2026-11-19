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

_UPPER_STRICT = r'(?:\b(?:di\s?bawah|under|kurang\s+dari)\b|<(?!=))'
_UPPER_INCLUSIVE = r'(?:\b(?:maksimal|maksimum|maks|max|(?:budget|anggaran)(?:\s+(?:saya|ku|aku|kami))?|tidak\s+lebih\s+dari|paling\s+mahal)\b|<=)'
_UPPER = rf'(?:{_UPPER_STRICT}|{_UPPER_INCLUSIVE})'

_LOWER_STRICT = r'(?:\b(?:di\s?atas|above|lebih\s+dari)\b|>(?!=))'
_LOWER_INCLUSIVE = r'(?:\b(?:minimal|minimum|min)\b|>=)'
_LOWER = rf'(?:{_LOWER_STRICT}|{_LOWER_INCLUSIVE})'

_AROUND = r'\b(?:sekitar|kisaran|around|harga|di\s+harga)\b|~'
_SEP = r'(?:-|–|—|sampai|sd|s/d|hingga|to)'

_COMP_UPPER_STRICT = r'(?:\b(?:di\s?bawah|under|kurang\s+dari)\b|<(?!=))'
_COMP_UPPER_INCL = r'(?:\b(?:maksimal|maksimum|maks|max|tidak\s+lebih\s+dari|paling\s+(?:berat|besar|tinggi))\b|<=)'
_COMP_LOWER_STRICT = r'(?:\b(?:di\s?atas|above|lebih\s+dari)\b|>(?!=))'
_COMP_LOWER_INCL = r'(?:\b(?:minimal|minimum|min)\b|>=)'
_COMP_OP = rf'(?:{_COMP_UPPER_STRICT}|{_COMP_UPPER_INCL}|{_COMP_LOWER_STRICT}|{_COMP_LOWER_INCL})'
_SUF_COMP_OP = r'\b(?:ke\s?bawah|ke\s?atas|maksimal|maksimum|maks|max|minimal|minimum|min)\b'


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
_NEG_TOUCH_RX = re.compile(
    r'\b(?:tanpa|no|non|bukan|jangan|tidak|nggak|enggak|gak|ga)\s+(?:pakai\s+|ada\s+|layar\s+)?'
    r'(?:touch\s*screen|layar\s+sentuh|layar\s+touch|sentuh)\b'
)
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

_RANGE_ANTARA_JUTA = re.compile(
    r'\bantara\s+(?:rp\.?\s*)?(?P<a>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)?\s*(?:dan|sampai|hingga|sd|s/d|-|–|—|to)\s*(?:rp\.?\s*)?(?P<b>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)\b'
)
_RANGE_ANTARA_PLAIN = re.compile(
    r'\bantara\s+(?:rp\.?\s*)?(?P<a>\d{1,3}(?:\.\d{3}){2,}|\d{6,9})\s*(?:dan|sampai|hingga|sd|s/d|-|–|—|to)\s*(?:rp\.?\s*)?(?P<b>\d{1,3}(?:\.\d{3}){2,}|\d{6,9})\b'
)
_RANGE_JUTA = re.compile(
    rf'(?:rp\.?\s*)?(?P<a>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)?\s*{_SEP}\s*(?:rp\.?\s*)?(?P<b>\d+(?:[.,]\d+)?)\s*(?:jutaan|juta|jtan|jt)\b'
)
_RANGE_PLAIN = re.compile(
    rf'(?:rp\.?\s*)?(?P<a>\d{{1,3}}(?:\.\d{{3}}){{2,}}|\d{{6,9}})\s*{_SEP}\s*(?:rp\.?\s*)?(?P<b>\d{{1,3}}(?:\.\d{{3}}){{2,}}|\d{{6,9}})\b'
)
_MONEY = re.compile(
    r'(?:(?:rp\.?\s*)?(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>jutaan|juta|jtan|jt)\b'
    r'|rp\.?\s*(?P<rp_full>\d{1,3}(?:\.\d{3})+|\d{6,9})\b'
    r'|(?P<full>\b\d{1,3}(?:\.\d{3}){2,}\b)'
    r'|(?P<plain>\b\d{6,9}\b))'
)

_SSD_A = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\bssd\s*(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>tb|gb)(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)
_SSD_B = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>tb|gb)\s*ssd'
    rf'(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)

_HDD_A = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?:hdd|harddisk|hard\s*disk)\s*(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>tb|gb)(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)
_HDD_B = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?P<v>\d+(?:[.,]\d+)?)\s*(?P<u>tb|gb)\s*(?:hdd|harddisk|hard\s*disk)'
    rf'(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)

_RAM_EXP_A = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\bram\s*(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'(?P<v>\d{{1,4}})\s*(?:gb|g)?(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)
_RAM_EXP_B = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?P<v>\d{{1,4}})\s*(?:gb|g)\s*ram'
    rf'(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b)'
)

_STORAGE_TB = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?:storage|penyimpanan|kapasitas|memori)\s*(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'|(?:(?P<op3>{_COMP_OP})\s+)?\b)'
    rf'(?P<v>\d+(?:[.,]\d+)?)\s*tb(?:\s*(?P<op4>{_SUF_COMP_OP}))?\b'
)
_STORAGE_GB = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?:storage|penyimpanan|kapasitas|memori)\s*(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'|(?:(?P<op3>{_COMP_OP})\s+)?\b)'
    rf'(?P<v>128|256|500|512|1000|1024)\s*gb(?:\s*(?P<op4>{_SUF_COMP_OP}))?\b'
)

_WEIGHT = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\bberat\s*(?:(?P<op2>{_COMP_OP})\s*)?(?P<v>\d+(?:[.,]\d+)?)\s*kg(?:\s*(?P<op3>{_SUF_COMP_OP}))?\b'
    rf'|(?:(?P<op4>{_COMP_OP})\s+)?\b(?P<v2>\d+(?:[.,]\d+)?)\s*kg(?:\s*(?P<op5>{_SUF_COMP_OP}))?\b)'
)

_RAM_BARE = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?\b(?P<v>\d{{1,2}})\s*(?:gb|g)(?:\s*(?P<op2>{_SUF_COMP_OP}))?\b)'
)

_SCREEN = re.compile(
    rf'(?:(?:(?P<op1>{_COMP_OP})\s+)?(?:layar\s*)?(?:(?P<op2>{_COMP_OP})\s*)?'
    rf'\b(?P<v>\d{{2}}(?:[.,]\d)?)\s*(?:inch|inci|in\b|")(?:\s*(?P<op3>{_SUF_COMP_OP}))?)'
)

_OS_PATTERNS = [
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:windows|win)\s*11\b'), "windows 11"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:windows|win)\s*10\s*s\b'), "windows 10 s"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:windows|win)\s*10\b'), "windows 10"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:windows|win)\s*8(?:\.1)?\b'), "windows 8"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:windows|win)\s*7\b'), "windows 7"),
    (re.compile(r'\b(?:tanpa\s+os|no\s+os|free\s*dos|tanpa\s+windows|bebas\s+os)\b'), "no os"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?(?:linux|ubuntu)\b'), "linux"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?chrome\s*os\b'), "chrome os"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?mac\s*os(?:\s*x)?\b'), "macos"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?android\b(?!\s+studio)'), "android"),
    (re.compile(r'\b(?:(?:os|dengan)\s+)?windows\b'), "windows"),
]

_GPU_MODEL_RX = re.compile(
    r'\b(?:(?:nvidia\s+)?(?:geforce\s+)?(?P<nv>(?:rtx|gtx)\s*\d{3,4}(?:\s*(?:ti|super|max-q))?|mx\s*\d{3}|9[45678]0mx?)'
    r'|(?:nvidia\s+)?(?P<quadro>quadro\s*[a-z]?\d{3,4}m?)'
    r'|(?:amd\s+)?(?:radeon\s+)?(?P<rx>rx\s*\d{3,4}(?:\s*xt|m)?)'
    r'|(?:intel\s+)?(?P<arc>arc\s*a\d{3}m?))\b'
)
_CPU_APPLE_EXPLICIT_RX = re.compile(r'\bapple\s+(?P<am>m[1-4](?:\s+(?:pro|max|ultra))?)\b')
_CPU_APPLE_SHORT_RX = re.compile(r'\b(?P<am>m[1-4](?:\s+(?:pro|max|ultra))?)\b')
_CPU_ULTRA_RX = re.compile(r'\b(?:intel\s+)?core\s+ultra\s+(?P<tier>[579])\b')
_CPU_INTEL_I_RX = re.compile(r'\b(?P<intel>intel\s+)?(?:core\s+)?(?P<tier>i[3579])(?:[\s-]+(?P<sku>\d{4,5}[a-z]{0,2}))?\b')
_CPU_RYZEN_TIER_RX = re.compile(r'\b(?:amd\s+)?ryzen\s+(?P<tier>[3579]|\d{4}[a-z]{0,2})\b')
_CPU_OTHER_RX = re.compile(r'\b(?:intel\s+)?(?P<fam>celeron|pentium|xeon|atom)\b')

_TOUCH_RX = re.compile(r'\b(?:(?:wajib|harus)\s+)?(?:touch\s*screen|layar\s+sentuh|layar\s+touch)\b')
_CONVERTIBLE_RX = re.compile(r'\b(?:2\s*in\s*1|2in1|convertible|bisa\s+dilipat)\b')


def _fmt_idr(val: int) -> str:
    return f"Rp{val:,.0f}".replace(",", ".")


def _fmt_gb(gb: int) -> str:
    return f"{gb // 1000}TB" if gb >= 1000 and gb % 1000 == 0 else f"{gb}GB"


def _to_float(s: str) -> float:
    return float(s.replace(',', '.'))


def _parse_money_token(raw: str) -> int:
    return int(raw.replace('.', ''))


def _money_value(m: re.Match) -> int:
    if m.group('rp_full'):
        return _parse_money_token(m.group('rp_full'))
    if m.group('full'):
        return _parse_money_token(m.group('full'))
    if m.group('plain'):
        return int(m.group('plain'))
    return int(round(_to_float(m.group('num')) * 1_000_000))


def _classify_op(op: Optional[str], default_dir: str = 'min') -> Tuple[str, bool]:
    if not op:
        return default_dir, True
    op_l = re.sub(r'\s+', ' ', op.lower().strip())
    if re.match(r'^(?:di\s?bawah|under|kurang\s+dari|<)$', op_l):
        return 'max', False
    if re.match(r'^(?:maksimal|maksimum|maks|max|tidak\s+lebih\s+dari|paling\s+(?:berat|besar|tinggi)|<=|ke\s?bawah)$', op_l):
        return 'max', True
    if re.match(r'^(?:di\s?atas|above|lebih\s+dari|>)$', op_l):
        return 'min', False
    if re.match(r'^(?:minimal|minimum|min|>=|ke\s?atas)$', op_l):
        return 'min', True
    return default_dir, True


def _apply_price_min(c: "Constraints", value: int, inclusive: bool):
    if c.price_min is None or value > c.price_min:
        c.price_min = value
        c.price_min_inclusive = inclusive
    elif value == c.price_min:
        c.price_min_inclusive = c.price_min_inclusive and inclusive
    c.price_around_target = None


def _apply_price_max(c: "Constraints", value: int, inclusive: bool):
    if c.price_max is None or value < c.price_max:
        c.price_max = value
        c.price_max_inclusive = inclusive
    elif value == c.price_max:
        c.price_max_inclusive = c.price_max_inclusive and inclusive
    c.price_around_target = None


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
    ram_max: Optional[int] = None
    ram_max_inclusive: bool = True
    ram_source: str = "user"
    ram_reason: Optional[str] = None

    storage_min_gb: Optional[int] = None
    storage_min_inclusive: bool = True
    storage_max_gb: Optional[int] = None
    storage_max_inclusive: bool = True
    ssd_min_gb: Optional[int] = None
    ssd_min_inclusive: bool = True
    ssd_max_gb: Optional[int] = None
    ssd_max_inclusive: bool = True
    hdd_min_gb: Optional[int] = None
    hdd_min_inclusive: bool = True
    hdd_max_gb: Optional[int] = None
    hdd_max_inclusive: bool = True
    exclude_hdd: bool = False

    weight_min_kg: Optional[float] = None
    weight_min_inclusive: bool = True
    weight_max_kg: Optional[float] = None
    weight_max_inclusive: bool = True

    screen_inch: Optional[float] = None
    screen_min_inch: Optional[float] = None
    screen_min_inclusive: bool = True
    screen_max_inch: Optional[float] = None
    screen_max_inclusive: bool = True

    require_gaming_gpu: bool = False
    exclude_gaming: bool = False
    gaming_negated: bool = False
    require_creator_spec: bool = False

    prefer_cheap: bool = False
    sort_cheapest_explicit: bool = False
    prefer_lightweight: bool = False

    required_brand: Optional[str] = None
    allowed_brands: List[str] = field(default_factory=list)
    excluded_brands: List[str] = field(default_factory=list)
    required_family: Optional[str] = None
    required_model_tokens: List[str] = field(default_factory=list)
    required_os: Optional[str] = None
    required_gpu: Optional[str] = None
    required_cpu: Optional[str] = None
    require_touchscreen: bool = False
    exclude_touchscreen: bool = False
    require_convertible: bool = False

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
            and self.ram_max is None
            and self.storage_min_gb is None
            and self.storage_max_gb is None
            and self.ssd_min_gb is None
            and self.ssd_max_gb is None
            and self.hdd_min_gb is None
            and self.hdd_max_gb is None
            and not self.exclude_hdd
            and self.weight_min_kg is None
            and self.weight_max_kg is None
            and self.screen_inch is None
            and self.screen_min_inch is None
            and self.screen_max_inch is None
            and not self.require_gaming_gpu
            and not self.exclude_gaming
            and not self.require_creator_spec
            and not self.prefer_cheap
            and not self.sort_cheapest_explicit
            and not self.prefer_lightweight
            and self.required_brand is None
            and not self.allowed_brands
            and not self.excluded_brands
            and self.required_family is None
            and not self.required_model_tokens
            and self.required_os is None
            and self.required_gpu is None
            and self.required_cpu is None
            and not self.require_touchscreen
            and not self.exclude_touchscreen
            and not self.require_convertible
        )

    def build_applied_filters(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        if self.price_min is not None and self.price_max is not None:
            if self.price_around_target is not None:
                label = f"harga {_fmt_idr(self.price_min)} - {_fmt_idr(self.price_max)} (sekitar {_fmt_idr(self.price_around_target)})"
                items.append({"key": "price_range", "label": label, "source": "user", "kind": "hard"})
            elif self.price_min > self.price_max or not self.price_min_inclusive or not self.price_max_inclusive:
                op_min = ">=" if self.price_min_inclusive else ">"
                op_max = "<=" if self.price_max_inclusive else "<"
                items.append({"key": "price_min", "label": f"harga {op_min} {_fmt_idr(self.price_min)}", "source": "user", "kind": "hard"})
                items.append({"key": "price_max", "label": f"harga {op_max} {_fmt_idr(self.price_max)}", "source": "user", "kind": "hard"})
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
        if self.ram_max is not None:
            op = "<=" if self.ram_max_inclusive else "<"
            items.append({"key": "ram_max", "label": f"RAM {op} {self.ram_max}GB", "source": "user", "kind": "hard"})

        if self.ssd_min_gb is not None:
            op = ">=" if self.ssd_min_inclusive else ">"
            items.append({"key": "ssd_min_gb", "label": f"SSD {op} {_fmt_gb(self.ssd_min_gb)}", "source": "user", "kind": "hard"})
        if self.ssd_max_gb is not None:
            op = "<=" if self.ssd_max_inclusive else "<"
            items.append({"key": "ssd_max_gb", "label": f"SSD {op} {_fmt_gb(self.ssd_max_gb)}", "source": "user", "kind": "hard"})

        if self.hdd_min_gb is not None:
            op = ">=" if self.hdd_min_inclusive else ">"
            items.append({"key": "hdd_min_gb", "label": f"HDD {op} {_fmt_gb(self.hdd_min_gb)}", "source": "user", "kind": "hard"})
        if self.hdd_max_gb is not None:
            op = "<=" if self.hdd_max_inclusive else "<"
            items.append({"key": "hdd_max_gb", "label": f"HDD {op} {_fmt_gb(self.hdd_max_gb)}", "source": "user", "kind": "hard"})

        if self.storage_min_gb is not None:
            op = ">=" if self.storage_min_inclusive else ">"
            items.append({"key": "storage_min_gb", "label": f"Storage {op} {_fmt_gb(self.storage_min_gb)}", "source": "user", "kind": "hard"})
        if self.storage_max_gb is not None:
            op = "<=" if self.storage_max_inclusive else "<"
            items.append({"key": "storage_max_gb", "label": f"Storage {op} {_fmt_gb(self.storage_max_gb)}", "source": "user", "kind": "hard"})

        if self.exclude_hdd:
            items.append({"key": "exclude_hdd", "label": "tanpa HDD", "source": "user", "kind": "hard"})

        if self.weight_min_kg is not None:
            op = ">=" if self.weight_min_inclusive else ">"
            items.append({"key": "weight_min_kg", "label": f"berat {op} {self.weight_min_kg:g} kg", "source": "user", "kind": "hard"})
        if self.weight_max_kg is not None:
            op = "<=" if self.weight_max_inclusive else "<"
            items.append({"key": "weight_max_kg", "label": f"berat {op} {self.weight_max_kg:g} kg", "source": "user", "kind": "hard"})

        if self.screen_min_inch is not None:
            op = ">=" if self.screen_min_inclusive else ">"
            items.append({"key": "screen_min_inch", "label": f"layar {op} {self.screen_min_inch:g} inch", "source": "user", "kind": "hard"})
        if self.screen_max_inch is not None:
            op = "<=" if self.screen_max_inclusive else "<"
            items.append({"key": "screen_max_inch", "label": f"layar {op} {self.screen_max_inch:g} inch", "source": "user", "kind": "hard"})
        if self.screen_inch is not None:
            items.append({"key": "screen_inch", "label": f"layar ~{self.screen_inch:g} inch", "source": "user", "kind": "hard"})

        if self.allowed_brands:
            if len(self.allowed_brands) == 1:
                items.append({"key": "brand", "label": f"merek {self.allowed_brands[0]}", "source": "user", "kind": "hard"})
            else:
                items.append({"key": "allowed_brands", "label": f"merek {' atau '.join(self.allowed_brands)}", "source": "user", "kind": "hard"})
        elif self.required_brand:
            items.append({"key": "brand", "label": f"merek {self.required_brand}", "source": "user", "kind": "hard"})
        if self.excluded_brands:
            items.append({"key": "excluded_brands", "label": f"bukan merek {', '.join(self.excluded_brands)}", "source": "user", "kind": "hard"})

        if self.required_family and self.required_model_tokens:
            items.append({"key": "family", "label": f"seri {self.required_family} {' '.join(self.required_model_tokens)}", "source": "user", "kind": "hard"})
        elif self.required_family:
            items.append({"key": "family", "label": f"seri {self.required_family}", "source": "user", "kind": "hard"})
        elif self.required_model_tokens:
            items.append({"key": "model", "label": f"model {' '.join(self.required_model_tokens)}", "source": "user", "kind": "hard"})

        if self.required_cpu:
            items.append({"key": "cpu", "label": f"CPU {self.required_cpu}", "source": "user", "kind": "hard"})
        if self.required_gpu:
            items.append({"key": "gpu", "label": f"GPU {self.required_gpu}", "source": "user", "kind": "hard"})
        if self.required_os:
            items.append({"key": "os", "label": f"OS {self.required_os}", "source": "user", "kind": "hard"})
        if self.require_convertible:
            items.append({"key": "require_convertible", "label": "kategori 2-in-1 Convertible", "source": "user", "kind": "hard"})
        if self.require_touchscreen:
            items.append({"key": "require_touchscreen", "label": "layar touchscreen", "source": "user", "kind": "hard"})
        if self.exclude_touchscreen:
            items.append({"key": "exclude_touchscreen", "label": "tanpa touchscreen", "source": "user", "kind": "hard"})

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

    for m in _NEG_TOUCH_RX.finditer(text):
        c.exclude_touchscreen = True
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
    normalized = query.lower().replace('≤', '<=').replace('≥', '>=')
    text = re.sub(r'\s+', ' ', normalized).strip()
    c = Constraints()

    # 1. Negasi diproses terlebih dahulu sebelum intent & expander
    text = _strip_negated_clauses(text, c)
    spans: List[Tuple[int, int]] = []

    # 2. Harga (rentang & klausa nominal tunggal/majemuk)
    for rx, is_juta in (
        (_RANGE_ANTARA_JUTA, True),
        (_RANGE_ANTARA_PLAIN, False),
        (_RANGE_JUTA, True),
        (_RANGE_PLAIN, False),
    ):
        for m_r in rx.finditer(text):
            if is_juta:
                v1 = int(round(_to_float(m_r.group('a')) * 1_000_000))
                v2 = int(round(_to_float(m_r.group('b')) * 1_000_000))
            else:
                v1 = _parse_money_token(m_r.group('a'))
                v2 = _parse_money_token(m_r.group('b'))
            _apply_price_min(c, min(v1, v2), True)
            _apply_price_max(c, max(v1, v2), True)
            start, end = m_r.span()
            prefix = text[max(0, start - 32):start]
            cue = re.search(r'(?:harga\s+)?(?:budget|anggaran|harga|kisaran|sekitar)(?:\s+(?:saya|ku|aku|kami))?\s*$', prefix)
            if cue:
                start -= len(cue.group(0))
            spans.append((start, end))
        if spans:
            break

    text_after_ranges = _cut(text, spans)
    spans = []
    prev_end = 0
    explicit_price_bound = (c.price_min is not None or c.price_max is not None)

    for m in _MONEY.finditer(text_after_ranges):
        value = _money_value(m)
        start, end = m.start(), m.end()
        prefix = text_after_ranges[max(prev_end, start - 35):start]
        suffix = text_after_ranges[end:end + 22]

        suf_u_incl = re.match(r'\s*(?:ke\s?bawah|maks(?:imal|imum)?|max)\b', suffix)
        suf_l_incl = re.match(r'\s*(?:ke\s?atas|minimal|minimum|min)\b', suffix)

        cue_u_strict = re.search(r'(?:harga\s+)?' + _UPPER_STRICT + r'\s*$', prefix)
        cue_u_incl = re.search(r'(?:harga\s+)?' + _UPPER_INCLUSIVE + r'\s*$', prefix)
        cue_l_strict = re.search(r'(?:harga\s+)?' + _LOWER_STRICT + r'\s*$', prefix)
        cue_l_incl = re.search(r'(?:harga\s+)?' + _LOWER_INCLUSIVE + r'\s*$', prefix)
        cue_a = re.search(r'(?:' + _AROUND + r')\s*$', prefix)

        if cue_u_strict:
            _apply_price_max(c, value, False)
            explicit_price_bound = True
            start -= len(cue_u_strict.group(0))
        elif cue_u_incl or suf_u_incl:
            _apply_price_max(c, value, True)
            explicit_price_bound = True
            if cue_u_incl:
                start -= len(cue_u_incl.group(0))
            if suf_u_incl:
                end += len(suf_u_incl.group(0))
                lead_cue = re.search(r'(?:harga|budget|anggaran)(?:\s+(?:saya|ku|aku|kami))?\s*$', prefix)
                if lead_cue:
                    start -= len(lead_cue.group(0))
        elif cue_l_strict:
            _apply_price_min(c, value, False)
            explicit_price_bound = True
            start -= len(cue_l_strict.group(0))
        elif cue_l_incl or suf_l_incl:
            _apply_price_min(c, value, True)
            explicit_price_bound = True
            if cue_l_incl:
                start -= len(cue_l_incl.group(0))
            if suf_l_incl:
                end += len(suf_l_incl.group(0))
                lead_cue = re.search(r'(?:harga|budget|anggaran)(?:\s+(?:saya|ku|aku|kami))?\s*$', prefix)
                if lead_cue:
                    start -= len(lead_cue.group(0))
        elif not explicit_price_bound and c.price_min is None and c.price_max is None:
            _apply_price_min(c, int(round(value * (1 - AROUND_RATIO))), True)
            _apply_price_max(c, int(round(value * (1 + AROUND_RATIO))), True)
            c.price_around_target = value
            if cue_a:
                start -= len(cue_a.group(0))
        prev_end = max(prev_end, m.end())
        spans.append((start, end))

    text_no_price = _cut(text_after_ranges, spans)
    spans = []

    # 3a. SSD eksplisit (termasuk desimal koma seperti 0,5 TB & batas atas)
    for rx in (_SSD_A, _SSD_B):
        m = rx.search(text_no_price)
        if m:
            val = _to_float(m.group('v'))
            gb = int(round(val * 1000)) if m.group('u') == 'tb' else int(round(val))
            op = m.group('op1') or (m.groupdict().get('op2')) or m.group('op3')
            direction, inclusive = _classify_op(op, default_dir='min')
            if direction == 'max':
                c.ssd_max_gb = gb
                c.ssd_max_inclusive = inclusive
            else:
                c.ssd_min_gb = gb
                c.ssd_min_inclusive = inclusive
            spans.append(m.span())
            break

    text_no_ssd = _cut(text_no_price, spans)
    spans = []

    # 3b. HDD eksplisit
    for rx in (_HDD_A, _HDD_B):
        m = rx.search(text_no_ssd)
        if m:
            val = _to_float(m.group('v'))
            gb = int(round(val * 1000)) if m.group('u') == 'tb' else int(round(val))
            op = m.group('op1') or (m.groupdict().get('op2')) or m.group('op3')
            direction, inclusive = _classify_op(op, default_dir='min')
            if direction == 'max':
                c.hdd_max_gb = gb
                c.hdd_max_inclusive = inclusive
            else:
                c.hdd_min_gb = gb
                c.hdd_min_inclusive = inclusive
            spans.append(m.span())
            break

    text_no_hdd = _cut(text_no_ssd, spans)
    spans = []

    # 3c. RAM eksplisit sebelum storage umum agar 'RAM 128GB' tidak bocor ke storage
    for rx in (_RAM_EXP_A, _RAM_EXP_B):
        m = rx.search(text_no_hdd)
        if m:
            ram_val = int(m.group('v'))
            if ram_val > 0:
                op = m.group('op1') or (m.groupdict().get('op2')) or m.group('op3')
                direction, inclusive = _classify_op(op, default_dir='min')
                if direction == 'max':
                    c.ram_max = ram_val
                    c.ram_max_inclusive = inclusive
                else:
                    c.ram_min = ram_val
                    c.ram_min_inclusive = inclusive
                c.ram_source = "user"
                spans.append(m.span())
                break

    text_no_ram_exp = _cut(text_no_hdd, spans)
    spans = []

    # 3d. Storage umum (eksplisit atau angka kapasitas standar)
    m_tb = _STORAGE_TB.search(text_no_ram_exp)
    m_gb = _STORAGE_GB.search(text_no_ram_exp)
    if m_tb and 0.25 <= _to_float(m_tb.group('v')) <= 16.0:
        gb = int(round(_to_float(m_tb.group('v')) * 1000))
        op = m_tb.group('op1') or m_tb.group('op2') or m_tb.group('op3') or m_tb.group('op4')
        direction, inclusive = _classify_op(op, default_dir='min')
        if direction == 'max':
            c.storage_max_gb = gb
            c.storage_max_inclusive = inclusive
        else:
            c.storage_min_gb = gb
            c.storage_min_inclusive = inclusive
        spans.append(m_tb.span())
    elif m_gb:
        gb = int(m_gb.group('v'))
        op = m_gb.group('op1') or m_gb.group('op2') or m_gb.group('op3') or m_gb.group('op4')
        direction, inclusive = _classify_op(op, default_dir='min')
        if direction == 'max':
            c.storage_max_gb = gb
            c.storage_max_inclusive = inclusive
        else:
            c.storage_min_gb = gb
            c.storage_min_inclusive = inclusive
        spans.append(m_gb.span())

    text_no_storage = _cut(text_no_ram_exp, spans)
    spans = []

    # 4. Berat (kg)
    m_w = _WEIGHT.search(text_no_storage)
    if m_w:
        v_str = m_w.group('v') or m_w.group('v2')
        w_val = _to_float(v_str)
        if 0.3 <= w_val <= 10.0:
            op = m_w.group('op1') or m_w.group('op2') or m_w.group('op3') or m_w.group('op4') or m_w.group('op5')
            direction, inclusive = _classify_op(op, default_dir='max')
            if direction == 'min':
                c.weight_min_kg = w_val
                c.weight_min_inclusive = inclusive
            else:
                c.weight_max_kg = w_val
                c.weight_max_inclusive = inclusive
            spans.append(m_w.span())

    # 5. Layar (inch)
    m_scr = _SCREEN.search(text_no_storage)
    if m_scr and 10 <= _to_float(m_scr.group('v')) <= 18.5:
        scr_val = _to_float(m_scr.group('v'))
        op = m_scr.group('op1') or m_scr.group('op2') or m_scr.group('op3')
        if op:
            direction, inclusive = _classify_op(op, default_dir='min')
            if direction == 'max':
                c.screen_max_inch = scr_val
                c.screen_max_inclusive = inclusive
            else:
                c.screen_min_inch = scr_val
                c.screen_min_inclusive = inclusive
        else:
            c.screen_inch = scr_val
        spans.append(m_scr.span())

    # 6. Bare RAM (tanpa kata 'ram', hanya nilai valid)
    if c.ram_min is None and c.ram_max is None:
        m_rb = _RAM_BARE.search(text_no_storage)
        if m_rb and int(m_rb.group('v')) in VALID_RAM_GB:
            op = m_rb.group('op1') or m_rb.group('op2')
            direction, inclusive = _classify_op(op, default_dir='min')
            if direction == 'max':
                c.ram_max = int(m_rb.group('v'))
                c.ram_max_inclusive = inclusive
            else:
                c.ram_min = int(m_rb.group('v'))
                c.ram_min_inclusive = inclusive
            c.ram_source = "user"
            spans.append(m_rb.span())

    clean_remaining = _cut(text_no_storage, spans)

    # 6b. OS, GPU, CPU, Touchscreen & 2-in-1 Convertible eksplisit
    spec_spans: List[Tuple[int, int]] = []
    for rx, os_val in _OS_PATTERNS:
        m_os = rx.search(clean_remaining)
        if m_os:
            c.required_os = os_val
            spec_spans.append(m_os.span())
            break

    clean_no_os = _cut(clean_remaining, spec_spans)
    spec_spans = []

    m_gpu = _GPU_MODEL_RX.search(clean_no_os)
    if m_gpu:
        raw_gpu = m_gpu.group('nv') or m_gpu.group('quadro') or m_gpu.group('rx') or m_gpu.group('arc')
        c.required_gpu = re.sub(r'\s+', ' ', raw_gpu).strip()
        spec_spans.append(m_gpu.span())

    clean_no_gpu = _cut(clean_no_os, spec_spans)
    spec_spans = []

    m_cpu = _CPU_APPLE_EXPLICIT_RX.search(clean_no_gpu)
    if m_cpu:
        am = re.sub(r'\s+', ' ', m_cpu.group('am')).strip()
        c.required_cpu = f"apple {am}"
        spec_spans.append(m_cpu.span())
    else:
        m_am = _CPU_APPLE_SHORT_RX.search(clean_no_gpu)
        if m_am and re.search(r'\b(?:macbook|apple|macos)\b', _cut(clean_no_gpu, [m_am.span()])):
            before_am = clean_no_gpu[:m_am.start()].rstrip()
            if not before_am.endswith('core m'):
                am = re.sub(r'\s+', ' ', m_am.group('am')).strip()
                c.required_cpu = f"apple {am}"
                spec_spans.append(m_am.span())
        if c.required_cpu is None:
            m_cu = _CPU_ULTRA_RX.search(clean_no_gpu)
            m_ci = _CPU_INTEL_I_RX.search(clean_no_gpu) if not m_cu else None
            m_ry = _CPU_RYZEN_TIER_RX.search(clean_no_gpu) if not (m_cu or m_ci) else None
            m_ot = _CPU_OTHER_RX.search(clean_no_gpu) if not (m_cu or m_ci or m_ry) else None
            if m_cu:
                c.required_cpu = f"core ultra {m_cu.group('tier')}"
                spec_spans.append(m_cu.span())
            elif m_ci:
                parts = []
                if m_ci.group('intel'):
                    parts.append('intel')
                parts.extend(['core', m_ci.group('tier')])
                if m_ci.group('sku'):
                    parts.append(m_ci.group('sku'))
                c.required_cpu = " ".join(parts)
                spec_spans.append(m_ci.span())
            elif m_ry:
                c.required_cpu = f"ryzen {m_ry.group('tier')}"
                spec_spans.append(m_ry.span())
            elif m_ot:
                c.required_cpu = m_ot.group('fam')
                spec_spans.append(m_ot.span())

    clean_no_cpu = _cut(clean_no_gpu, spec_spans)
    spec_spans = []

    if not c.exclude_touchscreen:
        m_touch = _TOUCH_RX.search(clean_no_cpu)
        if m_touch:
            c.require_touchscreen = True
            spec_spans.append(m_touch.span())

    m_conv = _CONVERTIBLE_RX.search(clean_no_cpu)
    if m_conv:
        c.require_convertible = True
        spec_spans.append(m_conv.span())

    clean_remaining = _cut(clean_no_cpu, spec_spans)

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
        if c.ram_min is None and (c.ram_max is None or c.ram_max >= 8):
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "gaming"
    elif _CREATOR_INTENT.search(clean_remaining):
        c.require_creator_spec = True
        if c.ram_min is None and (c.ram_max is None or c.ram_max >= 8):
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "edit video/desain"
    elif _CODING_INTENT.search(clean_remaining):
        if c.ram_min is None and (c.ram_max is None or c.ram_max >= 8):
            c.ram_min = 8
            c.ram_source = "system_assumption"
            c.ram_reason = "coding/ngoding"

    c.build_applied_filters()
    return c, clean_remaining

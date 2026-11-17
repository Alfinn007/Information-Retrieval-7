import re
from dataclasses import dataclass
from typing import Optional, Tuple

VALID_RAM_GB = {2, 4, 6, 8, 12, 16, 24, 32, 64}
SCREEN_TOLERANCE = 0.6
AROUND_RATIO = 0.2

_UPPER = r'(?:di\s?bawah|under|kurang\s+dari|maksimal|maksimum|maks|max|budget|tidak\s+lebih\s+dari|paling\s+mahal|<=?)'
_LOWER = r'(?:di\s?atas|above|lebih\s+dari|minimal|minimum|min|paling\s+murah|>=?)'
_AROUND = r'(?:sekitar|kisaran|around|harga|di\s+harga|~)'
_SEP = r'(?:-|sampai|sd|s/d|hingga|to)'

_CHEAP_INTENT = re.compile(
    r'\b(murah|terjangkau|budget|hemat|murmer|ekonomis|low\s+end|entry\s+level|pas\s+kantong|harga\s+miring|harga\s+bersahabat)\b'
)
_GAMING_INTENT = re.compile(
    r'\b(gaming|game|gamer|ngegame|main\s+game|esport|e-sport|valorant|dota|pubg|fortnite|genshin|gta|pes|fifa|battlefield)\b'
)
_CREATOR_INTENT = re.compile(
    r'\b(edit\s+video|video\s+edit|editing\s+video|ngedit|render|rendering|animasi|3d|premiere|after\s+effects|blender|davinci|autocad|sketchup|arsitek|workstation)\b'
)
_CODING_INTENT = re.compile(
    r'\b(coding|ngoding|programmer|programming|pemrograman|developer|software\s+engineer|web\s+dev|data\s+science|machine\s+learning|android\s+studio|vscode|informatika|ilmu\s+komputer)\b'
)

_MONEY = re.compile(
    r'(?:rp\.?\s*(?P<full>\d{1,3}(?:\.\d{3})+)'
    r'|(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>jutaan|juta|jtan|jt))'
)
_RANGE = re.compile(
    rf'(?P<a>\d+(?:[.,]\d+)?)\s*(?:juta|jt)?\s*{_SEP}\s*(?P<b>\d+(?:[.,]\d+)?)\s*(?:juta|jt)\b'
)
_RAM_A = re.compile(r'\bram\s*(?:minimal|min|>=?)?\s*(?P<v>\d{1,2})\s*(?:gb|g)?\b')
_RAM_B = re.compile(r'\b(?P<v>\d{1,2})\s*(?:gb|g)\s*(?:ram)?\b')

_STORAGE_TB = re.compile(r'\b(?P<v>[12])(?:\.0)?\s*tb\b')
_STORAGE_GB = re.compile(r'\b(?P<v>128|256|500|512)\s*gb\b')

_SCREEN = re.compile(r'(?:layar\s*)?\b(?P<v>\d{2}(?:[.,]\d)?)\s*(?:inch|inci|in\b|")')


@dataclass
class Constraints:
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    ram_min: Optional[int] = None
    storage_min_gb: Optional[int] = None
    screen_inch: Optional[float] = None
    require_gaming_gpu: bool = False
    require_creator_spec: bool = False
    sort_cheapest: bool = False

    @property
    def is_empty(self) -> bool:
        return (self.price_min is None and self.price_max is None
                and self.ram_min is None and self.storage_min_gb is None
                and self.screen_inch is None and not self.require_gaming_gpu
                and not self.require_creator_spec and not self.sort_cheapest)

    def describe(self) -> str:
        parts = []
        if self.price_min is not None and self.price_max is not None:
            parts.append(f"harga Rp{self.price_min:,.0f} - Rp{self.price_max:,.0f}".replace(',', '.'))
        elif self.price_min is not None:
            parts.append(f"harga >= Rp{self.price_min:,.0f}".replace(',', '.'))
        elif self.price_max is not None:
            parts.append(f"harga <= Rp{self.price_max:,.0f}".replace(',', '.'))

        if self.ram_min is not None:
            parts.append(f"RAM >= {self.ram_min}GB")
        if self.storage_min_gb is not None:
            label = f"{self.storage_min_gb // 1000}TB" if self.storage_min_gb >= 1000 else f"{self.storage_min_gb}GB"
            parts.append(f"Storage >= {label}")
        if self.screen_inch is not None:
            parts.append(f"layar ~{self.screen_inch} inch")
        if self.require_gaming_gpu:
            parts.append("GPU Gaming (GTX/RTX/Radeon RX)")
        elif self.require_creator_spec:
            parts.append("GPU Dedicated (Quadro/MX/GTX)")
        if self.sort_cheapest:
            parts.append("prioritas harga termurah")
        return ", ".join(parts) if parts else "Tidak ada filter khusus"


def _to_float(s: str) -> float:
    return float(s.replace(',', '.'))


def _money_value(m: re.Match) -> int:
    if m.group('full'):
        return int(m.group('full').replace('.', ''))
    return int(round(_to_float(m.group('num')) * 1_000_000))


def _cut(text: str, spans) -> str:
    chars = list(text)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = ' '
    return re.sub(r'\s+', ' ', ''.join(chars)).strip()


def parse_constraints(query: str) -> Tuple[Constraints, str]:
    text = query.lower()
    c = Constraints()
    spans = []

    m = _RANGE.search(text)
    if m:
        c.price_min = int(_to_float(m.group('a')) * 1_000_000)
        c.price_max = int(_to_float(m.group('b')) * 1_000_000)
        if c.price_min > c.price_max:
            c.price_min, c.price_max = c.price_max, c.price_min
        spans.append(m.span())
    else:
        m = _MONEY.search(text)
        if m:
            value = _money_value(m)
            start, end = m.start(), m.end()
            prefix = text[max(0, start - 20):start]
            suffix = text[end:end + 20]
            suf_u = re.match(r'\s*(?:ke\s?bawah|maks(?:imal)?|max)\b', suffix)
            suf_l = re.match(r'\s*(?:ke\s?atas|minimal|min)\b', suffix)
            cue_u = re.search(_UPPER + r'\s*$', prefix)
            cue_l = re.search(_LOWER + r'\s*$', prefix)
            cue_a = re.search(_AROUND + r'\s*$', prefix)
            if cue_u or suf_u:
                c.price_max = value
                if cue_u:
                    start -= len(cue_u.group(0))
                if suf_u:
                    end += len(suf_u.group(0))
            elif cue_l or suf_l:
                c.price_min = value
                if cue_l:
                    start -= len(cue_l.group(0))
                if suf_l:
                    end += len(suf_l.group(0))
            else:
                c.price_min = int(value * (1 - AROUND_RATIO))
                c.price_max = int(value * (1 + AROUND_RATIO))
                if cue_a:
                    start -= len(cue_a.group(0))
            spans.append((start, end))

    for rx in (_RAM_A, _RAM_B):
        m = rx.search(text)
        if m and int(m.group('v')) in VALID_RAM_GB:
            c.ram_min = int(m.group('v'))
            break

    m_tb = _STORAGE_TB.search(text)
    m_gb = _STORAGE_GB.search(text)
    if m_tb:
        c.storage_min_gb = int(m_tb.group('v')) * 1000
    elif m_gb:
        c.storage_min_gb = int(m_gb.group('v'))

    m = _SCREEN.search(text)
    if m and 10 <= _to_float(m.group('v')) <= 18.5:
        c.screen_inch = _to_float(m.group('v'))
        spans.append(m.span())

    if _GAMING_INTENT.search(text):
        c.require_gaming_gpu = True
        if c.ram_min is None:
            c.ram_min = 8
    elif _CREATOR_INTENT.search(text):
        c.require_creator_spec = True
        if c.ram_min is None:
            c.ram_min = 8
    elif _CODING_INTENT.search(text):
        if c.ram_min is None:
            c.ram_min = 8

    if _CHEAP_INTENT.search(text):
        c.sort_cheapest = True

    return c, _cut(text, spans)

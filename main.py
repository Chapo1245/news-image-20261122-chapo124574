#!/usr/bin/env python3
"""news-image-20261122 — "The Sunday World" (variant A).

Draws the 1024x1024 front page for Sunday 22 November 2026: 35 stories
across 7 regions, 3 lead stories, 10 illustrated scene cards, a dotted
world map with pins, 22 briefs, and a DATE CHECK of 9 excluded stale items.
All facts were verified against Reuters / BBC / AP / TOI / CNN wires for
22 November 2026; see README.md for the story list and sources.

Usage: python3 main.py  -> writes entry.png (1024x1024, PNG, <=1 MiB).
Deterministic: two runs produce a byte-identical file. No network access.
Requires: Pillow (PIL) and the DejaVu fonts shipped with most Linux distros.
"""
import hashlib
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 233)
INK = (22, 22, 20)
INK_SOFT = (58, 58, 54)
RED = (176, 32, 28)
BLUE = (28, 68, 120)
TEAL = (14, 110, 110)
GOLD = (176, 132, 24)
GREY_LINE = (170, 164, 150)
CARD_BG = (255, 255, 255)
SKY_DAY = (158, 196, 222)
SKY_NIGHT = (18, 28, 52)
SEA = (36, 98, 140)

# ---------------------------------------------------------------- fonts
_FDIR = "/usr/share/fonts/truetype/dejavu/"
_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _cache:
        path = {
            "serif": _FDIR + "DejaVuSerif.ttf",
            "serif_b": _FDIR + "DejaVuSerif-Bold.ttf",
            "sans": _FDIR + "DejaVuSans.ttf",
            "sans_b": _FDIR + "DejaVuSans-Bold.ttf",
        }[name]
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


def tw(f, s):
    """Pixel width of s in font f (measured, never guessed)."""
    return f.getlength(s)


def wrap(f, s, max_w):
    """Greedy word wrap; returns lines. Raises if a single word exceeds max_w."""
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if tw(f, trial) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            if tw(f, wd) > max_w:
                raise AssertionError(f"WORD TOO WIDE ({tw(f, wd):.0f}px > {max_w}px): {wd!r}")
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit_lines(f, s, max_w, max_lines, what):
    """Wrap s to <= max_lines lines each fitting max_w; raise with detail if not."""
    lines = wrap(f, s, max_w)
    if len(lines) > max_lines:
        raise AssertionError(
            f"TEXT OVERFLOW [{what}]: {len(lines)} lines > {max_lines} for {s!r} "
            f"(max_w={max_w})")
    return lines


def draw_lines(d, x, y, lines, f, fill, leading):
    for i, ln in enumerate(lines):
        d.text((x, y + i * leading), ln, font=f, fill=fill)
    return y + len(lines) * leading


# ---------------------------------------------------------------- story data
# kind: lead | scene | brief. scene_key names the illustration function.
# Every story carries: headline, deck ('' for briefs), source, region.
# Regions: Asia-Pacific, Europe, Middle East, Americas, Africa, Oceania, World.
STORIES = {
    # --- 3 large leads ---
    "cop31": dict(kind="lead", scene="cop31",
        headline="COP31 NEARS A DEAL",
        deck="New draft text after all-night talks; plenary votes Sunday. Fossil fuels still unnamed.",
        source="Reuters", region="World"),
    "gulf": dict(kind="lead", scene="gulf",
        headline="GULF ON FIRE",
        deck="Iran hits US assets in Bahrain; site ablaze. Tankers hit off Oman — TORKEL burning at anchor.",
        source="TOI / UKMTO", region="Middle East"),
    "ukraine": dict(kind="lead", scene="ukraine",
        headline="UKRAINE BARRAGE",
        deck="400 drones + 110 missiles: Lviv station hit; Kryvyi Rih 2 dead, 58 hurt; Kyiv bridges struck.",
        source="BBC", region="Europe"),
    # --- 10 scene cards ---
    "sparta": dict(kind="scene", scene="sparta",
        headline="SPARTA II ABLAZE",
        deck="Russian ship hit by 2 drones; fire rages, 16 crew evacuated.",
        source="CNN", region="Europe"),
    "hongkong": dict(kind="scene", scene="hongkong",
        headline="HONG KONG VOTES",
        deck="856 candidates chase 723 seats; 5,700 voters decide.",
        source="news.gov.hk", region="Asia-Pacific"),
    "cepa": dict(kind="scene", scene="cepa",
        headline="EU–INDONESIA DEAL",
        deck="Tariffs fall on 98.5% of EU goods; ~€650m a year saved.",
        source="Reuters", region="Europe"),
    "cricket": dict(kind="scene", scene="cricket",
        headline="INDIA 720/9",
        deck="Pant 128, Rahul 136; record 720/9 declared, lead NZ by 352.",
        source="Reuters", region="Oceania"),
    "f1": dict(kind="scene", scene="f1",
        headline="VERSTAPPEN WINS VEGAS",
        deck="75th win by 0.6s over Norris; Russell crashes on lap 49.",
        source="PlanetF1", region="Americas"),
    "chapo": dict(kind="scene", scene="chapo",
        headline="EL CHAPO ISIDRO SEIZED",
        deck="FBI most-wanted boss captured; 11 dead in Sinaloa gun battles.",
        source="TOI", region="Americas"),
    "peru": dict(kind="scene", scene="peru",
        headline="PERU QUAKE AFTERMATH",
        deck="6.8 Junín quake: 15 hurt, 152 homes uninhabitable.",
        source="AppiSToS", region="Americas"),
    "hartha": dict(kind="scene", scene="hartha",
        headline="HARTHA FIRE",
        deck="Iraq power-station blaze kills 4, injures 35 near Basra.",
        source="AppiSToS", region="Middle East"),
    "maluku": dict(kind="scene", scene="maluku",
        headline="MALUKU QUAKE",
        deck="7.2 magnitude, 125 km deep; no tsunami, no damage reported.",
        source="World in Sixty", region="Asia-Pacific"),
    "houthi": dict(kind="scene", scene="houthi",
        headline="HOUTHI MISSILES",
        deck="3 missiles intercepted over Riyadh; coalition strikes Hodeidah.",
        source="FB World News", region="Middle East"),
    # --- briefs (headline only; source shown in parens) ---
    "trump_iran": dict(kind="brief", headline="Trump: Iran deal \u201ccould last 20 years\u201d",
        source="TOI", region="Americas"),
    "zelensky": dict(kind="brief", headline="Zelensky: Crimea Bridge strikes a \u201cfair response\u201d",
        source="BBC", region="Europe"),
    "denmark": dict(kind="brief", headline="Denmark: Russia plotted to kill US-Ukrainian rapper",
        source="BBC", region="Europe"),
    "roundup": dict(kind="brief", headline="Roundup $7.25bn cancer settlement approved",
        source="BBC", region="Americas"),
    "palisades": dict(kind="brief", headline="Palisades arson conviction",
        source="BBC", region="Americas"),
    "markets": dict(kind="brief", headline="MARKETS: S&P worst week since Apr 2025; tech sell-off",
        source="Daily Brief", region="World"),
    "zecler": dict(kind="brief", headline="French police jailed for beating Michel Zecler",
        source="BBC", region="Europe"),
    "ufo": dict(kind="brief", headline="Pentagon declassifies more UFO footage",
        source="BBC", region="Americas"),
    "nitish": dict(kind="brief", headline="Modi opens Nitish Setu bridge in Bihar",
        source="Jagran", region="Asia-Pacific"),
    "akvan": dict(kind="brief", headline="Cyclone Akvan: 14 flights cancelled at Ranchi",
        source="Jagran", region="Asia-Pacific"),
    "airlines": dict(kind="brief", headline="Airlines warned of al-Qaeda threat before Thanksgiving",
        source="TOI", region="Americas"),
    "bolsonaro": dict(kind="brief", headline="Bolsonaro in ICU with bowel obstruction",
        source="TOI", region="Americas"),
    "yamagata": dict(kind="brief", headline="Yamagata snow 49 cm; bullet trains suspended",
        source="todaynewsnation", region="Asia-Pacific"),
    "nigeria": dict(kind="brief", headline="Nigeria boat capsize: 24 dead en route to funeral",
        source="AP", region="Africa"),
    "cardcap": dict(kind="brief", headline="Trump vows 10% cap on credit-card rates",
        source="AP", region="Americas"),
    "japan_india": dict(kind="brief", headline="Japan troops to train live-fire in India, a first",
        source="Jagran", region="Asia-Pacific"),
    "football": dict(kind="brief", headline="Leeds stun Chelsea 4–1; Newcastle 2–2 Arsenal",
        source="BBC/Sky", region="Europe"),
    "florida": dict(kind="brief", headline="Florida floods break a 73-year river record",
        source="FB World News", region="Americas"),
    "manipur": dict(kind="brief", headline="Manipur toxic alcohol: 11 dead, 180+ in hospital",
        source="FB World News", region="Asia-Pacific"),
    "finland_heli": dict(kind="brief", headline="Finland: suspected Russian helicopter incursion",
        source="AppiSToS", region="Europe"),
    "bangladesh": dict(kind="brief", headline="Bangladesh: 90 guard platoons curb arson",
        source="World in Sixty", region="Asia-Pacific"),
    "spain": dict(kind="brief", headline="Spain extends bank levy to 2027, €1.4bn for housing",
        source="Daily Brief", region="Europe"),
    # --- variant C extras ---
    "hair": dict(kind="brief", headline="Washington's hair lock sells for $4,000",
        source="BBC", region="Americas"),
    "atp": dict(kind="brief", headline="Alcaraz to face Zverev in ATP Finals decider",
        source="HuddleWorld", region="Europe"),
    "eubudget": dict(kind="brief", headline="EU proposes €1.78tn budget for 2028–2034",
        source="AppiSToS", region="Europe"),
    "wolbachia": dict(kind="brief", headline="Wolbachia mosquitoes cut dengue in Brazilian children",
        source="Astrova", region="Americas"),
}

VARIANTS = {
    "A": dict(
        title="Sunday 22 November 2026: 35 stories, 7 regions — COP31 near a deal, Gulf on fire, Sparta II ablaze",
        leads=["cop31", "gulf", "ukraine"],
        scenes=["sparta", "hongkong", "cepa", "cricket", "f1", "chapo", "peru", "hartha", "maluku", "houthi"],
        briefs=["trump_iran", "zelensky", "denmark", "roundup", "palisades", "markets",
                "zecler", "ufo", "nitish", "akvan", "airlines", "bolsonaro", "yamagata",
                "nigeria", "cardcap", "japan_india", "football", "florida", "manipur",
                "finland_heli", "bangladesh", "spain"],
        timeline=False),
    "B": dict(
        title="Sunday 22 November 2026: 30 stories, 7 regions — COP31 near a deal, Gulf on fire, Sparta II ablaze",
        leads=["cop31", "gulf", "ukraine", "sparta"],
        scenes=["hongkong", "cepa", "cricket", "f1", "chapo", "peru", "hartha", "maluku"],
        briefs=["trump_iran", "zelensky", "denmark", "roundup", "palisades", "markets",
                "nitish", "akvan", "airlines", "bolsonaro", "nigeria", "japan_india",
                "football", "florida", "manipur", "finland_heli", "bangladesh", "houthi"],
        timeline=False),
    "C": dict(
        title="Sunday 22 November 2026: 39 stories, 7 regions — COP31 near a deal, Gulf on fire, Sparta II ablaze",
        leads=["cop31", "gulf", "ukraine"],
        scenes=["sparta", "hongkong", "cepa", "cricket", "f1", "chapo", "peru", "hartha", "maluku", "houthi"],
        briefs=["trump_iran", "zelensky", "denmark", "roundup", "palisades", "markets",
                "zecler", "ufo", "nitish", "akvan", "airlines", "bolsonaro", "yamagata",
                "nigeria", "cardcap", "japan_india", "football", "florida", "manipur",
                "finland_heli", "bangladesh", "spain",
                "hair", "atp", "eubudget", "wolbachia"],
        timeline=True),
}

STATS = [
    ("400+110", "drones + missiles\nat Ukraine"),
    ("720/9", "India declare\nrecord in NZ"),
    ("723", "Hong Kong\nseats voted"),
    ("35%", "electrification\nby 2035, COP31"),
    ("0.6s", "Verstappen's\nwinning margin"),
    ("€650m", "saved a year\nby EU–Indonesia deal"),
]

DATE_CHECK = ("DATE CHECK — NOT 22 NOV: Peru quake itself (20 Nov) · ICJ Myanmar ruling (19 Nov) · "
              "Kerch Bridge attack (19 Nov) · Anthropic IPO (19–20 Nov) · Fiona the hippo (19–20 Nov) · "
              "Trump–Xi–Putin summit (19–20 Nov) · Estonia border closure announced ~16 Nov · "
              "BepiColombo Mercury arrival (21 Nov) · Kenya Ebola countdown began 12 Nov.")

FOOTER = ("Sources: Reuters, BBC, AP, TOI, CNN, news.gov.hk, PlanetF1, AppiSToS, Jagran, Daily Brief. "
          "Events of 22 Nov 2026 in any time zone; late 21 Nov UTC events fall on 22 Nov in Asia-Pacific.")

REGION_ORDER = ["Asia-Pacific", "Europe", "Middle East", "Americas", "Africa", "Oceania", "World"]


def count_regions(ids):
    counts = {r: 0 for r in REGION_ORDER}
    for i in ids:
        counts[STORIES[i]["region"]] += 1
    return counts


def check_variant(name):
    v = VARIANTS[name]
    ids = v["leads"] + v["scenes"] + v["briefs"]
    assert len(ids) == len(set(ids)), f"{name}: duplicate story ids"
    counts = count_regions(ids)
    total = sum(counts.values())
    expect = {"A": 35, "B": 30, "C": 39}[name]
    assert total == expect, f"{name}: {total} stories != {expect}"
    assert all(counts[r] > 0 for r in REGION_ORDER), f"{name}: empty region {counts}"
    return counts

# ---------------------------------------------------------------- drawing helpers
def sky(d, x, y, w, h, top, bottom):
    """Vertical gradient sky (deterministic, no randomness)."""
    w, h = int(w), int(h)
    for i in range(h):
        t = i / max(1, h - 1)
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        d.line([(x, y + i), (x + w, y + i)], fill=c)


def sea(d, x, y, w, h):
    x, y, w, h = int(x), int(y), int(w), int(h)
    for i in range(h):
        t = i / max(1, h - 1)
        base = (28, 84, 128)
        c = tuple(int(base[k] * (1 - 0.25 * t)) for k in range(3))
        d.line([(x, y + i), (x + w, y + i)], fill=c)
    # wave lines
    for j in range(1, 4):
        yy = y + h * j // 4
        for xx in range(x, x + w, 26):
            d.arc([xx, yy - 3, xx + 22, yy + 3], 180, 360, fill=(190, 220, 235))


def flame(d, cx, base_y, w, h, n=3):
    """Layered flame: outer orange, mid yellow, core pale. Deterministic."""
    cols = [(214, 82, 20), (238, 150, 30), (250, 208, 80)]
    for k in range(n):
        fw = w * (1 - k * 0.28)
        fh = h * (1 - k * 0.30)
        x0, x1 = cx - fw / 2, cx + fw / 2
        y0, y1 = base_y - fh, base_y
        pts = [(x0, y1), (x0 + fw * 0.15, y1 - fh * 0.55),
               (x0 + fw * 0.38, y1 - fh * 0.45), (cx - fw * 0.08, y0),
               (cx + fw * 0.12, y1 - fh * 0.55), (x0 + fw * 0.85, y1 - fh * 0.4),
               (x1, y1)]
        d.polygon(pts, fill=cols[k % 3])


def smoke(d, x, y, w, h, n=4):
    """Rising smoke inside the (x, y, w, h) box: small overlapping
    circles, shrinking as they rise, NEVER above y (the box top)."""
    for i in range(n):
        r = max(3.0, min(w, h * 1.6) * (0.14 + 0.03 * i))
        cx = x + w * (0.25 + 0.5 * (i % 2)) + (4 if i % 2 else -4)
        frac = i / max(1, n - 1)
        cy = (y + h - r) - (h - 2 * r) * frac
        if cy - r < y:
            cy = y + r
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(128, 128, 128))


def stars(d, x, y, w, h):
    pts = [(0.08, 0.12), (0.25, 0.05), (0.42, 0.18), (0.58, 0.07), (0.74, 0.15),
           (0.9, 0.06), (0.15, 0.3), (0.35, 0.28), (0.65, 0.3), (0.85, 0.26)]
    for px, py in pts:
        cx, cy = x + w * px, y + h * py
        d.ellipse([cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5], fill=(235, 235, 220))


def skyline(d, x, base_y, w, h, color, heights):
    """Row of buildings from a fixed height pattern (fractions of h)."""
    n = len(heights)
    bw = w / n
    for i, hf in enumerate(heights):
        bx = x + i * bw
        bh = h * hf
        d.rectangle([bx + 1, base_y - bh, bx + bw - 1, base_y], fill=color)
        # windows: 2 columns of tiny lit squares
        for wy in range(2, int(bh) - 4, 9):
            for wx in (bx + bw * 0.28, bx + bw * 0.62):
                d.rectangle([wx, base_y - wy - 3, wx + 3, base_y - wy], fill=(255, 214, 110))


# ---------------------------------------------------------------- scenes
# Each scene draws into box (x, y, w, h). All fresh, hand-built shapes.

def scene_cop31(d, x, y, w, h):
    sky(d, x, y, w, h, (168, 205, 228), (232, 240, 244))
    d.ellipse([x + w * 0.78, y + h * 0.06, x + w * 0.94, y + h * 0.06 + w * 0.16], fill=(250, 200, 60))
    # distant coast + sea
    d.rectangle([x, y + h * 0.62, x + w, y + h * 0.72], fill=(52, 120, 150))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(214, 205, 182))
    # flag row on poles
    flag_cols = [(28, 68, 120), (176, 32, 28), (14, 110, 110), (176, 132, 24),
                 (90, 40, 110), (34, 120, 60), (200, 90, 20)]
    n = len(flag_cols)
    for i, fc in enumerate(flag_cols):
        px = x + w * (0.06 + 0.88 * i / (n - 1))
        d.line([(px, y + h * 0.30), (px, y + h * 0.62)], fill=(60, 60, 60), width=2)
        d.polygon([(px, y + h * 0.30), (px + w * 0.09, y + h * 0.35), (px, y + h * 0.40)], fill=fc)
    # document with check
    dx, dy, dw, dh = x + w * 0.30, y + h * 0.66, w * 0.40, h * 0.30
    d.rectangle([dx, dy, dx + dw, dy + dh], fill=(255, 255, 255), outline=(40, 40, 40))
    f = font("sans_b", max(9, int(h * 0.10)))
    d.text((dx + dw * 0.08, dy + dh * 0.06), "COP31", font=f, fill=(28, 68, 120))
    d.line([(dx + dw * 0.10, dy + dh * 0.52), (dx + dw * 0.28, dy + dh * 0.78),
            (dx + dw * 0.78, dy + dh * 0.30)], fill=(34, 140, 60), width=3)


def scene_gulf(d, x, y, w, h):
    sky(d, x, y, w, h, (14, 20, 38), (52, 36, 30))
    stars(d, x, y, w, int(h * 0.4))
    # industrial site silhouette
    base = y + h * 0.66
    d.rectangle([x, base, x + w, y + h], fill=(30, 26, 24))
    for bx, bw, bh in [(0.04, 0.10, 0.34), (0.18, 0.08, 0.44), (0.30, 0.12, 0.30),
                       (0.62, 0.09, 0.40), (0.76, 0.12, 0.32)]:
        d.rectangle([x + w * bx, base - h * bh, x + w * (bx + bw), base], fill=(52, 48, 44))
    d.rectangle([x + w * 0.46, base - h * 0.52, x + w * 0.52, base], fill=(52, 48, 44))
    # flames over the plant
    flame(d, x + w * 0.24, base, w * 0.30, h * 0.34)
    flame(d, x + w * 0.68, base, w * 0.24, h * 0.26)
    smoke(d, x + w * 0.55, y + h * 0.05, w * 0.3, h * 0.3, n=3)
    # tanker on water at the bottom
    sea(d, x, y + h * 0.82, w, h * 0.18)
    d.polygon([(x + w * 0.08, y + h * 0.86), (x + w * 0.46, y + h * 0.86),
               (x + w * 0.42, y + h * 0.97), (x + w * 0.12, y + h * 0.97)], fill=(20, 20, 20))
    d.rectangle([x + w * 0.30, y + h * 0.80, x + w * 0.40, y + h * 0.86], fill=(20, 20, 20))
    flame(d, x + w * 0.27, y + h * 0.86, w * 0.10, h * 0.12, n=2)


def scene_ukraine(d, x, y, w, h):
    sky(d, x, y, w, h, (12, 18, 40), (40, 34, 52))
    stars(d, x, y, w, int(h * 0.45))
    # missile trails
    for (x0, y0, x1, y1) in [(0.10, 0.42, 0.30, 0.18), (0.55, 0.38, 0.72, 0.12),
                             (0.78, 0.45, 0.92, 0.28)]:
        d.line([(x + w * x0, y + h * y0), (x + w * x1, y + h * y1)],
               fill=(255, 170, 60), width=3)
        d.ellipse([x + w * x1 - 3, y + h * y1 - 3, x + w * x1 + 3, y + h * y1 + 3],
                  fill=(255, 220, 120))
    # city skyline + station
    base = y + h
    skyline(d, x, base - h * 0.22, w, h * 0.22, (26, 26, 34),
            [0.9, 0.6, 1.0, 0.7, 0.85, 0.55, 0.95, 0.65])
    # station building with damaged roof + smoke
    sx, sw, sh = x + w * 0.30, w * 0.40, h * 0.24
    d.rectangle([sx, base - sh, sx + sw, base - h * 0.22], fill=(120, 96, 70))
    d.polygon([(sx - 4, base - sh), (sx + sw / 2, base - sh - h * 0.10),
               (sx + sw + 4, base - sh)], fill=(80, 60, 44))
    d.rectangle([sx + sw * 0.62, base - sh - h * 0.10, sx + sw * 0.78, base - sh],
                fill=(40, 32, 26))
    smoke(d, sx + sw * 0.55, base - sh - h * 0.34, w * 0.3, h * 0.3, n=3)
    flame(d, sx + sw * 0.70, base - sh - h * 0.02, w * 0.14, h * 0.14, n=2)


def scene_sparta(d, x, y, w, h):
    sky(d, x, y, w, h, (70, 96, 130), (150, 170, 185))
    sea(d, x, y + h * 0.58, w, h * 0.42)
    # cargo ship
    hull_y = y + h * 0.58
    d.polygon([(x + w * 0.06, hull_y), (x + w * 0.90, hull_y),
               (x + w * 0.84, hull_y + h * 0.16), (x + w * 0.12, hull_y + h * 0.16)],
              fill=(32, 32, 36))
    # containers
    for i, cc in enumerate([(176, 32, 28), (28, 68, 120), (176, 132, 24), (14, 110, 110)]):
        cx = x + w * (0.14 + i * 0.17)
        d.rectangle([cx, hull_y - h * 0.13, cx + w * 0.14, hull_y], fill=cc)
    # bridge tower
    d.rectangle([x + w * 0.80, hull_y - h * 0.24, x + w * 0.88, hull_y], fill=(220, 220, 210))
    # big fire amidships + smoke
    flame(d, x + w * 0.48, hull_y, w * 0.34, h * 0.42)
    flame(d, x + w * 0.62, hull_y, w * 0.22, h * 0.30)
    smoke(d, x + w * 0.40, y + h * 0.02, w * 0.35, h * 0.30, n=4)
    # lifeboat
    d.ellipse([x + w * 0.08, y + h * 0.86, x + w * 0.22, y + h * 0.93], fill=(240, 110, 20))


def scene_hongkong(d, x, y, w, h):
    sky(d, x, y, w, h, (150, 190, 220), (225, 232, 236))
    base = y + h * 0.72
    skyline(d, x, base, w, h * 0.42, (58, 72, 92),
            [0.7, 1.0, 0.55, 0.85, 0.65, 0.95, 0.5, 0.8])
    # pointed tower
    tx = x + w * 0.44
    d.polygon([(tx, base - h * 0.62), (tx + w * 0.07, base - h * 0.62),
               (tx + w * 0.035, base - h * 0.72)], fill=(58, 72, 92))
    # ballot box in front (bigger, VOTE legible)
    bx, bw, bh = x + w * 0.32, w * 0.36, h * 0.30
    by = y + h - bh - 2
    d.rectangle([bx, by, bx + bw, by + bh], fill=(245, 245, 240), outline=(30, 30, 30))
    d.rectangle([bx + bw * 0.22, by + h * 0.02, bx + bw * 0.78, by + h * 0.06], fill=(30, 30, 30))
    # ballot paper going in
    d.polygon([(bx + bw * 0.42, by - h * 0.16), (bx + bw * 0.62, by - h * 0.16),
               (bx + bw * 0.58, by + h * 0.02), (bx + bw * 0.46, by + h * 0.02)],
              fill=(255, 255, 255), outline=(30, 30, 30))
    f = font("sans_b", max(9, int(h * 0.11)))
    d.text((bx + bw * 0.18, by + bh * 0.42), "VOTE", font=f, fill=(176, 32, 28))


def scene_cepa(d, x, y, w, h):
    sky(d, x, y, w, h, (170, 205, 228), (238, 240, 242))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(196, 188, 168))
    # two flag poles
    for fx, flag in [(0.16, "eu"), (0.58, "id")]:
        px = x + w * fx
        d.line([(px, y + h * 0.18), (px, y + h * 0.74)], fill=(60, 60, 60), width=2)
        fw, fh = w * 0.30, h * 0.20
        if flag == "eu":
            d.rectangle([px, y + h * 0.18, px + fw, y + h * 0.18 + fh], fill=(28, 68, 150))
            for k in range(8):
                ang = 3.14159 * 2 * k / 8
                sx = px + fw * 0.5 + fw * 0.28 * 0.9 * __import__("math").cos(ang)
                sy = y + h * 0.18 + fh * 0.5 + fh * 0.28 * 0.9 * __import__("math").sin(ang)
                d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 210, 60))
        else:
            d.rectangle([px, y + h * 0.18, px + fw, y + h * 0.18 + fh / 2], fill=(200, 40, 36))
            d.rectangle([px, y + h * 0.18 + fh / 2, px + fw, y + h * 0.18 + fh], fill=(245, 245, 245))
    # signed document between the flags
    dx, dy, dw, dh = x + w * 0.36, y + h * 0.52, w * 0.28, h * 0.34
    d.rectangle([dx, dy, dx + dw, dy + dh], fill=(255, 255, 255), outline=(40, 40, 40))
    f = font("sans_b", max(8, int(h * 0.09)))
    d.text((dx + dw * 0.14, dy + dh * 0.08), "CEPA", font=f, fill=(28, 68, 120))
    d.line([(dx + dw * 0.12, dy + dh * 0.55), (dx + dw * 0.45, dy + dh * 0.80),
            (dx + dw * 0.85, dy + dh * 0.38)], fill=(34, 140, 60), width=3)


def scene_cricket(d, x, y, w, h):
    sky(d, x, y, w, h, (140, 185, 215), (215, 230, 235))
    d.rectangle([x, y + h * 0.60, x + w, y + h], fill=(52, 128, 62))
    # pitch strip
    d.rectangle([x + w * 0.36, y + h * 0.60, x + w * 0.64, y + h], fill=(196, 172, 120))
    # stumps
    for i in range(3):
        sx = x + w * (0.44 + i * 0.035)
        d.line([(sx, y + h * 0.66), (sx, y + h * 0.74)], fill=(250, 220, 90), width=3)
    # batsman: head, body, bat
    bx, by = x + w * 0.52, y + h * 0.72
    d.ellipse([bx - w * 0.035, by - h * 0.10, bx + w * 0.035, by - h * 0.03], fill=(30, 30, 30))
    d.line([(bx, by - h * 0.03), (bx, by + h * 0.12)], fill=(30, 30, 30), width=4)
    d.line([(bx, by + h * 0.12), (bx - w * 0.03, y + h * 0.96)], fill=(30, 30, 30), width=3)
    d.line([(bx, by + h * 0.12), (bx + w * 0.04, y + h * 0.96)], fill=(30, 30, 30), width=3)
    d.line([(bx + w * 0.02, by + h * 0.02), (bx + w * 0.13, by - h * 0.12)],
           fill=(150, 105, 50), width=4)
    # scoreboard
    sw, sh = w * 0.46, h * 0.24
    sx, sy = x + w * 0.27, y + h * 0.06
    d.rectangle([sx, sy, sx + sw, sy + sh], fill=(18, 18, 18))
    f = font("sans_b", max(9, int(h * 0.13)))
    t = "720/9"
    d.text((sx + (sw - tw(f, t)) / 2, sy + sh * 0.12), t, font=f, fill=(255, 215, 90))


def scene_f1(d, x, y, w, h):
    sky(d, x, y, w, h, (10, 12, 30), (30, 22, 52))
    stars(d, x, y, w, int(h * 0.35))
    # neon track
    d.rectangle([x, y + h * 0.62, x + w, y + h], fill=(16, 16, 20))
    d.line([(x, y + h * 0.62), (x + w, y + h * 0.62)], fill=(0, 220, 200), width=2)
    d.line([(x, y + h * 0.86), (x + w, y + h * 0.86)], fill=(255, 40, 90), width=2)
    # F1 car: low sleek body + wheels + wing + halo (bigger than v1 sketch)
    cy = y + h * 0.74
    d.polygon([(x + w * 0.10, cy), (x + w * 0.30, cy - h * 0.10),
               (x + w * 0.62, cy - h * 0.11), (x + w * 0.88, cy - h * 0.02),
               (x + w * 0.88, cy + h * 0.05), (x + w * 0.12, cy + h * 0.05)],
              fill=(176, 32, 28))
    d.rectangle([x + w * 0.80, cy - h * 0.16, x + w * 0.93, cy - h * 0.08], fill=(120, 20, 20))
    for wx in (0.24, 0.72):
        d.ellipse([x + w * wx, cy - h * 0.03, x + w * (wx + 0.09), cy + h * 0.09],
                  fill=(8, 8, 8), outline=(200, 200, 200))
    # checkered flag (bigger, top-left)
    fx, fy, fw = x + w * 0.06, y + h * 0.08, w * 0.28
    for r in range(3):
        for c in range(5):
            col = (245, 245, 245) if (r + c) % 2 == 0 else (15, 15, 15)
            d.rectangle([fx + c * fw / 5, fy + r * h * 0.06,
                         fx + (c + 1) * fw / 5, fy + (r + 1) * h * 0.06], fill=col)
    d.rectangle([fx, fy, fx + fw, fy + h * 0.18], outline=(200, 200, 200))
    d.line([(fx, fy), (fx, fy + h * 0.24)], fill=(200, 200, 200), width=2)
    f = font("sans_b", max(10, int(h * 0.14)))
    d.text((x + w * 0.72, y + h * 0.10), "P1", font=f, fill=(255, 215, 90))


def scene_chapo(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(226, 214, 188))
    # wanted poster
    px, py, pw, ph = x + w * 0.18, y + h * 0.04, w * 0.64, h * 0.92
    d.rectangle([px, py, px + pw, py + ph], fill=(252, 248, 236), outline=(40, 40, 40))
    f = font("sans_b", max(9, int(h * 0.11)))
    t = "WANTED"
    d.text((px + (pw - tw(f, t)) / 2, py + ph * 0.04), t, font=f, fill=(20, 20, 20))
    # silhouette head + wide-brim hat + shoulders (ph-based, not w-based)
    cx = px + pw / 2
    hr = ph * 0.16
    d.ellipse([cx - hr, py + ph * 0.24, cx + hr, py + ph * 0.24 + 2 * hr],
              fill=(40, 40, 40))
    d.ellipse([cx - ph * 0.30, py + ph * 0.20, cx + ph * 0.30, py + ph * 0.24],
              fill=(40, 40, 40))
    d.pieslice([cx - ph * 0.18, py + ph * 0.10, cx + ph * 0.18, py + ph * 0.34],
               180, 360, fill=(40, 40, 40))
    d.pieslice([cx - ph * 0.36, py + ph * 0.55, cx + ph * 0.36, py + ph * 0.88],
               180, 360, fill=(40, 40, 40))
    # CAPTURED stamp (low, over the shoulders — never over the face)
    f2 = font("sans_b", max(8, int(h * 0.09)))
    t2 = "CAPTURED"
    sw, sh = tw(f2, t2) + 8, f2.size + 6
    stamp = Image.new("RGBA", (int(sw) + 4, int(sh) + 4), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rectangle([2, 2, sw, sh], outline=(176, 32, 28), width=2)
    sd.text((4, 3), t2, font=f2, fill=(176, 32, 28))
    stamp = stamp.rotate(-14, expand=True, resample=Image.BICUBIC)
    d._image.paste(stamp, (int(px + pw * 0.5 - stamp.width / 2),
                            int(py + ph * 0.66)), stamp)


def scene_peru(d, x, y, w, h):
    sky(d, x, y, w, h, (150, 185, 215), (220, 228, 232))
    # Andes triangles
    for (bx, bw, bh, col) in [(0.0, 0.45, 0.55, (110, 100, 92)), (0.30, 0.5, 0.72, (88, 80, 74)),
                              (0.62, 0.45, 0.50, (120, 110, 100))]:
        d.polygon([(x + w * bx, y + h * 0.72), (x + w * (bx + bw / 2), y + h * (0.72 - bh)),
                   (x + w * (bx + bw), y + h * 0.72)], fill=col)
        # snowcap
        d.polygon([(x + w * (bx + bw / 2 - 0.05), y + h * (0.72 - bh * 0.82)),
                   (x + w * (bx + bw / 2), y + h * (0.72 - bh)),
                   (x + w * (bx + bw / 2 + 0.05), y + h * (0.72 - bh * 0.82))],
                  fill=(245, 245, 245))
    # ground + cracks
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(168, 140, 104))
    for pts in [[(0.10, 0.74), (0.16, 0.82), (0.12, 0.90), (0.20, 0.97)],
                [(0.55, 0.74), (0.60, 0.84), (0.56, 0.92), (0.64, 0.98)],
                [(0.80, 0.75), (0.86, 0.83), (0.82, 0.90)]]:
        d.line([(x + w * px, y + h * py) for px, py in pts], fill=(60, 48, 36), width=3)
    # two tilted houses
    for hx, tilt in [(0.24, -8), (0.66, 7)]:
        house = Image.new("RGBA", (int(w * 0.22), int(h * 0.20)), (0, 0, 0, 0))
        hd = ImageDraw.Draw(house)
        hw, hh = w * 0.22, h * 0.20
        hd.rectangle([2, hh * 0.4, hw - 2, hh], fill=(214, 196, 160), outline=(60, 48, 36))
        hd.polygon([(0, hh * 0.4), (hw / 2, 2), (hw, hh * 0.4)], fill=(150, 60, 40))
        hd.rectangle([hw * 0.42, hh * 0.62, hw * 0.58, hh], fill=(60, 48, 36))
        house = house.rotate(tilt, expand=True, resample=Image.BICUBIC)
        d._image.paste(house, (int(x + w * hx), int(y + h * 0.72)), house)


def scene_hartha(d, x, y, w, h):
    sky(d, x, y, w, h, (60, 44, 36), (150, 96, 52))
    base = y + h
    # cooling towers
    for tx, tw2 in [(0.10, 0.26), (0.42, 0.26)]:
        x0 = x + w * tx
        d.polygon([(x0, base - h * 0.10), (x0 + w * 0.03, base - h * 0.52),
                   (x0 + tw2 * w - w * 0.03, base - h * 0.52),
                   (x0 + tw2 * w, base - h * 0.10)], fill=(150, 142, 128))
        d.ellipse([x0 + w * 0.01, base - h * 0.54, x0 + tw2 * w - w * 0.01, base - h * 0.48],
                  fill=(120, 112, 100))
    # chimney
    d.rectangle([x + w * 0.74, base - h * 0.62, x + w * 0.82, base - h * 0.10], fill=(110, 104, 96))
    flame(d, x + w * 0.23, base - h * 0.10, w * 0.22, h * 0.30)
    flame(d, x + w * 0.55, base - h * 0.10, w * 0.18, h * 0.22)
    smoke(d, x + w * 0.70, y + h * 0.05, w * 0.25, h * 0.30, n=3)


def scene_maluku(d, x, y, w, h):
    sky(d, x, y, w, h, (140, 185, 215), (210, 228, 234))
    sea(d, x, y + h * 0.55, w, h * 0.45)
    # big wave
    d.pieslice([x - w * 0.1, y + h * 0.30, x + w * 0.7, y + h * 0.95], 180, 360, fill=(52, 120, 160))
    d.pieslice([x + w * 0.3, y + h * 0.42, x + w * 1.05, y + h * 0.98], 180, 360, fill=(36, 98, 140))
    # seismograph strip
    sx, sy, sw, sh = x + w * 0.08, y + h * 0.08, w * 0.84, h * 0.34
    d.rectangle([sx, sy, sx + sw, sy + sh], fill=(255, 255, 255), outline=(40, 40, 40))
    mid = sy + sh / 2
    pts = []
    import math as _m
    for i in range(41):
        px = sx + sw * i / 40
        amp = (sh * 0.32 if 14 <= i <= 26 else sh * 0.07)
        py = mid + _m.sin(i * 1.7) * amp * (1 if i % 2 == 0 else -1)
        pts.append((px, py))
    d.line(pts, fill=(176, 32, 28), width=2)
    f = font("sans_b", max(10, int(h * 0.16)))
    d.text((sx + sw * 0.62, sy + sh * 0.55), "7.2", font=f, fill=(20, 20, 20))


def scene_houthi(d, x, y, w, h):
    sky(d, x, y, w, h, (12, 16, 38), (44, 36, 56))
    stars(d, x, y, w, int(h * 0.4))
    # Riyadh skyline with one tall thin tower
    base = y + h
    skyline(d, x, base - h * 0.18, w, h * 0.18, (24, 24, 32),
            [0.8, 0.6, 1.0, 0.7, 0.9, 0.6, 0.85, 0.7])
    tx = x + w * 0.46
    d.rectangle([tx, base - h * 0.62, tx + w * 0.05, base - h * 0.18], fill=(24, 24, 32))
    d.polygon([(tx - 2, base - h * 0.62), (tx + w * 0.025, base - h * 0.72),
               (tx + w * 0.05 + 2, base - h * 0.62)], fill=(24, 24, 32))
    # missile trails crossing + interception burst
    d.line([(x + w * 0.08, y + h * 0.55), (x + w * 0.48, y + h * 0.14)],
           fill=(255, 170, 60), width=3)
    d.line([(x + w * 0.92, y + h * 0.50), (x + w * 0.52, y + h * 0.16)],
           fill=(255, 210, 90), width=3)
    bx, by = x + w * 0.50, y + h * 0.15
    for ang in range(0, 360, 45):
        import math as _m
        ex = bx + 14 * _m.cos(_m.radians(ang))
        ey = by + 14 * _m.sin(_m.radians(ang))
        d.line([(bx, by), (ex, ey)], fill=(255, 240, 160), width=2)
    d.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(255, 240, 160))


SCENES = {
    "cop31": scene_cop31, "gulf": scene_gulf, "ukraine": scene_ukraine,
    "sparta": scene_sparta, "hongkong": scene_hongkong, "cepa": scene_cepa,
    "cricket": scene_cricket, "f1": scene_f1, "chapo": scene_chapo,
    "peru": scene_peru, "hartha": scene_hartha, "maluku": scene_maluku,
    "houthi": scene_houthi,
}

# ---------------------------------------------------------------- dotted world map
# Coarse continent outlines in (lon, lat). Hand-drawn approximations, good
# enough for a dotted map at ~470x170 px. No external data was used.

CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-130, 71), (-110, 68), (-95, 69), (-85, 66), (-80, 62),
     (-70, 58), (-60, 52), (-55, 47), (-65, 44), (-70, 42), (-75, 38), (-80, 32),
     (-81, 26), (-84, 30), (-90, 21), (-94, 17), (-90, 14), (-83, 9), (-79, 8),
     (-83, 12), (-88, 14), (-94, 16), (-97, 22), (-104, 20), (-110, 23), (-114, 28),
     (-117, 33), (-122, 37), (-124, 42), (-124, 48), (-130, 55), (-145, 60),
     (-155, 58), (-162, 55), (-168, 60)],
    # Greenland
    [(-58, 64), (-52, 60), (-43, 60), (-32, 64), (-22, 70), (-25, 76), (-40, 78),
     (-55, 76), (-60, 70)],
    # South America
    [(-79, 9), (-77, 4), (-72, 2), (-64, 0), (-55, -2), (-50, -5), (-40, -8),
     (-35, -10), (-38, -15), (-40, -22), (-48, -27), (-55, -34), (-62, -40),
     (-66, -47), (-70, -54), (-73, -50), (-73, -40), (-72, -30), (-71, -20),
     (-75, -15), (-79, -8), (-81, -4), (-80, 2)],
    # Africa
    [(-17, 15), (-16, 21), (-10, 28), (-6, 33), (0, 36), (9, 37), (11, 34),
     (20, 32), (30, 31), (33, 27), (37, 22), (40, 15), (44, 11), (51, 11),
     (48, 5), (41, -2), (40, -10), (36, -18), (33, -26), (28, -33), (20, -35),
     (16, -32), (13, -22), (12, -15), (9, -8), (9, 0), (9, 4), (-2, 5),
     (-8, 5), (-13, 8), (-17, 12)],
    # Europe
    [(-10, 37), (-9, 43), (-4, 44), (-2, 47), (0, 46), (2, 51), (5, 53), (8, 55),
     (8, 57), (12, 56), (18, 56), (21, 55), (24, 58), (28, 60), (30, 62), (28, 66),
     (25, 70), (20, 70), (15, 69), (12, 65), (10, 62), (6, 58), (4, 57),
     (-2, 54), (-5, 50), (-8, 48), (-10, 43)],
    # UK
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (-1, 51)],
    # Asia
    [(28, 36), (32, 38), (36, 36), (40, 38), (44, 40), (48, 40), (52, 42),
     (56, 44), (60, 46), (65, 48), (70, 50), (75, 52), (80, 55), (85, 58),
     (90, 60), (95, 62), (100, 65), (105, 68), (110, 70), (115, 72), (120, 72),
     (130, 72), (140, 72), (150, 70), (160, 68), (170, 66), (178, 65), (175, 62),
     (170, 60), (162, 56), (158, 52), (150, 48), (144, 44), (140, 40), (135, 35),
     (130, 33), (127, 35), (122, 32), (120, 28), (115, 22), (110, 20), (108, 15),
     (105, 9), (103, 6), (100, 8), (97, 12), (94, 16), (91, 22), (88, 22),
     (85, 19), (82, 16), (80, 10), (77, 8), (75, 12), (72, 20), (68, 23),
     (64, 25), (60, 25), (56, 26), (52, 28), (50, 30), (48, 30), (44, 32),
     (40, 36), (36, 36), (32, 36)],
    # Australia
    [(113, -22), (114, -28), (115, -33), (120, -34), (126, -32), (132, -32),
     (136, -35), (140, -38), (146, -39), (150, -37), (153, -32), (153, -27),
     (150, -22), (146, -19), (142, -11), (140, -17), (136, -15), (132, -12),
     (128, -14), (124, -16), (120, -19), (116, -20), (113, -22)],
    # SE Asia islands (rough blobs)
    [(95, 5), (98, 4), (100, 2), (102, 0), (104, -2), (100, -4), (96, -2), (94, 3)],
    [(108, -2), (112, -4), (114, -6), (110, -8), (106, -6)],
    [(118, -2), (122, -4), (124, -6), (120, -8)],
    [(130, -2), (134, -4), (136, -6), (132, -8)],
    [(138, -6), (142, -8), (146, -8), (142, -4), (138, -2)],
    [(120, 10), (122, 12), (124, 10), (122, 8)],
    [(124, 8), (126, 6), (124, 4)],
    # Japan
    [(130, 31), (131, 32), (133, 34), (135, 34), (137, 35), (139, 36), (140, 38),
     (141, 40), (142, 42), (143, 44), (141, 44), (140, 40), (138, 37), (136, 35),
     (134, 34), (132, 33), (130, 32)],
]

LAT_TOP, LAT_BOT = 74, -54


def _in_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xin = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < xin:
                inside = not inside
    return inside


def _on_land(lon, lat):
    return any(_in_poly(lon, lat, p) for p in CONTINENTS)


def draw_map(d, x, y, w, h, pins):
    """Dotted world map + red pins (lon, lat)."""
    step = 3.6
    lon = -180.0
    while lon <= 180:
        lat = LAT_TOP
        while lat >= LAT_BOT:
            if _on_land(lon, lat):
                px = x + (lon + 180) / 360 * w
                py = y + (LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * h
                d.ellipse([px - 1.6, py - 1.6, px + 1.6, py + 1.6], fill=(52, 72, 96))
            lat -= step
        lon += step
    for (plon, plat) in pins:
        px = x + (plon + 180) / 360 * w
        py = y + (LAT_TOP - plat) / (LAT_TOP - LAT_BOT) * h
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=RED)
        d.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=(255, 255, 255))


MAP_PINS = [(30.7, 36.9), (50.6, 26.2), (24.0, 49.8), (24.0, 60.0), (114.2, 22.3),
            (174.8, -41.3)]  # Antalya, Bahrain, Lviv, Gulf of Finland, Hong Kong, Wellington

REGION_COLORS = {
    "Asia-Pacific": (28, 68, 120), "Europe": (14, 110, 110), "Middle East": (176, 32, 28),
    "Americas": (176, 132, 24), "Africa": (90, 40, 110), "Oceania": (34, 120, 60),
    "World": (58, 58, 54),
}

TIMELINE = [
    ("00:41 UTC", "India 629/6"),
    ("03:00 UTC", "COP31 objections close"),
    ("05:37 UTC", "Verstappen wins Vegas"),
    ("06:00 UTC", "COP31 plenary"),
]


# ---------------------------------------------------------------- layout
# Per-variant geometry. All heights in px; the renderer asserts the total.
GEOM = {
    # card_row = height of ONE row of scene cards; section = 2*card_row + 8
    "A": dict(masthead=92, stats=40, lead_h=212, card_row=124, map_h=160,
              brief_row=14, brief_head=16, datecheck=26, footer=22, timeline=0),
    "B": dict(masthead=92, stats=36, lead_h=230, card_row=128, map_h=150,
              brief_row=15, brief_head=16, datecheck=26, footer=22, timeline=0),
    "C": dict(masthead=90, stats=40, lead_h=200, card_row=112, map_h=140,
              brief_row=14, brief_head=16, datecheck=26, footer=20, timeline=26),
}
GAP = 6
MARGIN = 16


def draw_masthead(d, y, h, nstories):
    f_name = font("serif_b", 24)
    f_date = font("serif_b", 38)
    f_tag = font("sans", 12)
    d.line([(MARGIN, y + 2), (W - MARGIN, y + 2)], fill=INK, width=2)
    name = "THE SUNDAY WORLD"
    d.text(((W - tw(f_name, name)) / 2, y + 4), name, font=f_name, fill=INK)
    date = "SUNDAY 22 NOVEMBER 2026"
    d.text(((W - tw(f_date, date)) / 2, y + 30), date, font=f_date, fill=RED)
    tag = f"{nstories} STORIES  ·  7 REGIONS  ·  ONE DAY, THE WHOLE WORLD"
    d.text(((W - tw(f_tag, tag)) / 2, y + h - 16), tag, font=f_tag, fill=INK_SOFT)
    d.line([(MARGIN, y + h - 2), (W - MARGIN, y + h - 2)], fill=INK, width=2)
    return y + h


def draw_stats(d, y, h):
    f_num = font("sans_b", 19)
    f_lab = font("sans", 9)
    col_w = (W - 2 * MARGIN) / len(STATS)
    for i, (num, lab) in enumerate(STATS):
        cx = MARGIN + col_w * i
        d.text((cx + (col_w - tw(f_num, num)) / 2, y + 2), num, font=f_num, fill=INK)
        for j, ln in enumerate(lab.split("\n")):
            d.text((cx + (col_w - tw(f_lab, ln)) / 2, y + 23 + j * 10), ln,
                   font=f_lab, fill=INK_SOFT)
        if i:
            d.line([(cx, y + 4), (cx, y + h - 4)], fill=GREY_LINE)
    return y + h


def draw_lead_panel(d, x, y, w, h, key):
    s = STORIES[key]
    d.rectangle([x, y, x + w, y + h], fill=CARD_BG, outline=GREY_LINE)
    art_h = 118 if h >= 210 else 104
    SCENES[s["scene"]](d, x + 1, y + 1, w - 2, art_h)
    d.line([(x, y + art_h + 1), (x + w, y + art_h + 1)], fill=GREY_LINE)
    tx = x + 8
    ty = y + art_h + 8
    f_h = font("sans_b", 19)
    lines = fit_lines(f_h, s["headline"], w - 16, 2, f"lead headline {key}")
    ty = draw_lines(d, tx, ty, lines, f_h, INK, 22)
    f_d = font("sans", 12)
    lines = fit_lines(f_d, s["deck"], w - 16, 3, f"lead deck {key}")
    ty = draw_lines(d, tx, ty + 2, lines, f_d, INK_SOFT, 14)
    assert ty <= y + h - 16, f"LEAD TEXT OVERFLOW [{key}]: text ends {ty}, panel ends {y + h}"
    f_s = font("sans", 9)
    d.text((tx, y + h - 14), f"Source: {s['source']}", font=f_s, fill=(120, 116, 108))
    return y + h


def draw_scene_card(d, x, y, w, h, key):
    s = STORIES[key]
    d.rectangle([x, y, x + w, y + h], fill=CARD_BG, outline=GREY_LINE)
    art_h = 48
    SCENES[s["scene"]](d, x + 1, y + 1, w - 2, art_h)
    d.line([(x, y + art_h + 1), (x + w, y + art_h + 1)], fill=GREY_LINE)
    tx = x + 6
    ty = y + art_h + 6
    f_h = font("sans_b", 13)
    lines = fit_lines(f_h, s["headline"], w - 12, 2, f"card headline {key}")
    ty = draw_lines(d, tx, ty, lines, f_h, INK, 15)
    f_d = font("sans", 10)
    lines = fit_lines(f_d, s["deck"], w - 12, 3, f"card deck {key}")
    ty = draw_lines(d, tx, ty + 1, lines, f_d, INK_SOFT, 12)
    assert ty <= y + h - 3, f"CARD TEXT OVERFLOW [{key}]: text ends {ty}, card ends {y + h}"
    return y + h


def draw_map_band(d, y, h, counts, n_illus):
    map_w = 470
    draw_map(d, MARGIN, y + 4, map_w, h - 8, MAP_PINS)
    f_cap = font("sans", 9)
    d.text((MARGIN, y + h - 12), "WORLD MAP — red pins: Antalya · Bahrain · Lviv · Gulf of Finland · Hong Kong · Wellington",
           font=f_cap, fill=INK_SOFT)
    # region chips, right column
    cx = MARGIN + map_w + 16
    cw = W - MARGIN - cx
    f_chip = font("sans_b", 12)
    f_num = font("sans_b", 12)
    rows = [(r, counts[r]) for r in REGION_ORDER if counts[r] > 0]
    chip_w = (cw - 8) / 2
    chip_h = 24
    for i, (r, n) in enumerate(rows):
        bx = cx + (i % 2) * (chip_w + 8)
        by = y + 4 + (i // 2) * (chip_h + 6)
        d.rectangle([bx, by, bx + chip_w, by + chip_h], fill=CARD_BG, outline=GREY_LINE)
        d.rectangle([bx, by, bx + 6, by + chip_h], fill=REGION_COLORS[r])
        d.text((bx + 12, by + 5), r.upper(), font=f_chip, fill=INK)
        d.text((bx + chip_w - 22, by + 5), str(n), font=f_num, fill=REGION_COLORS[r])
    ly = y + 4 + ((len(rows) + 1) // 2) * (chip_h + 6) + 2
    f_note = font("sans", 11)
    note = f"{n_illus} ILLUSTRATED SCENES  ·  9 DATE-CHECKED EXCLUSIONS BELOW"
    d.text((cx, ly), note, font=f_note, fill=INK_SOFT)
    return y + h


def draw_briefs(d, y, h, brief_ids, head_h, row_h):
    f_head = font("sans_b", 13)
    d.text((MARGIN, y), "ALSO TODAY", font=f_head, fill=RED)
    d.line([(MARGIN + 110, y + 8), (W - MARGIN, y + 8)], fill=GREY_LINE)
    y0 = y + head_h
    cols = 2
    per_col = (len(brief_ids) + cols - 1) // cols
    col_w = (W - 2 * MARGIN - 16) / cols
    f_b = font("sans", 12)
    f_n = font("sans_b", 12)
    for ci in range(cols):
        cx = MARGIN + ci * (col_w + 16)
        for ri in range(per_col):
            idx = ci * per_col + ri
            if idx >= len(brief_ids):
                break
            key = brief_ids[idx]
            s = STORIES[key]
            by = y0 + ri * row_h
            num = f"{idx + 1}."
            d.text((cx, by), num, font=f_n, fill=RED)
            txt = f"{s['headline']} ({s['source']})"
            max_w = col_w - tw(f_n, num) - 6
            if tw(f_b, txt) > max_w:
                raise AssertionError(
                    f"BRIEF TOO WIDE [{key}]: {tw(f_b, txt):.0f}px > {max_w:.0f}px: {txt!r}")
            d.text((cx + tw(f_n, num) + 6, by), txt, font=f_b, fill=INK)
    return y + h


def draw_timeline(d, y, h):
    f_h = font("sans_b", 11)
    f_t = font("sans", 11)
    d.text((MARGIN, y + 4), "UTC TIMELINE", font=f_h, fill=RED)
    x = MARGIN + 110
    d.line([(x, y + 12), (W - MARGIN, y + 12)], fill=GREY_LINE)
    n = len(TIMELINE)
    seg = (W - MARGIN - x) / n
    for i, (t, ev) in enumerate(TIMELINE):
        ex = x + seg * i
        d.ellipse([ex - 3, y + 9, ex + 3, y + 15], fill=RED)
        label = f"{t} — {ev}"
        if tw(f_t, label) > seg - 8:
            raise AssertionError(f"TIMELINE TOO WIDE: {label!r}")
        d.text((ex + 6, y + 2), label, font=f_t, fill=INK)
    return y + h


def draw_text_block(d, y, h, text, size, max_lines):
    f = font("sans", size)
    lines = fit_lines(f, text, W - 2 * MARGIN, max_lines, "text block")
    draw_lines(d, MARGIN, y + 2, lines, f, INK_SOFT, size + 2)
    return y + h


def render_variant(name):
    counts = check_variant(name)
    v = VARIANTS[name]
    g = GEOM[name]
    nstories = len(v["leads"]) + len(v["scenes"]) + len(v["briefs"])
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = 0
    y = draw_masthead(d, y, g["masthead"], nstories)
    y += GAP
    y = draw_stats(d, y, g["stats"])
    y += GAP
    # leads row
    nlead = len(v["leads"])
    lw = (W - 2 * MARGIN - (nlead - 1) * 8) / nlead
    for i, key in enumerate(v["leads"]):
        draw_lead_panel(d, MARGIN + i * (lw + 8), y, lw, g["lead_h"], key)
    y += g["lead_h"] + GAP
    # scene cards: 2 rows
    nsc = len(v["scenes"])
    per_row = (nsc + 1) // 2
    cw = (W - 2 * MARGIN - (per_row - 1) * 8) / per_row
    ch = g["card_row"]
    for r in range(2):
        for i in range(per_row):
            idx = r * per_row + i
            if idx >= nsc:
                break
            draw_scene_card(d, MARGIN + i * (cw + 8), y + r * (ch + 8), cw, ch,
                            v["scenes"][idx])
    y += 2 * ch + 8 + GAP
    # map band
    y = draw_map_band(d, y, g["map_h"], counts, len(v["leads"]) + len(v["scenes"]))
    y += GAP
    # briefs
    bh = g["brief_head"] + ((len(v["briefs"]) + 1) // 2) * g["brief_row"]
    y = draw_briefs(d, y, bh, v["briefs"], g["brief_head"], g["brief_row"])
    y += GAP
    # timeline (variant C only)
    if v["timeline"]:
        y = draw_timeline(d, y, g["timeline"])
        y += GAP
    # date check + footer
    y = draw_text_block(d, y, g["datecheck"], DATE_CHECK, 10, 2)
    y += GAP
    y = draw_text_block(d, y, g["footer"], FOOTER, 9, 2)
    assert y <= H, f"LAYOUT OVERFLOW: final y={y} > {H}"
    return img


def main():
    check_variant("A")
    img = render_variant("A")
    assert img.size == (1024, 1024), f"size {img.size}"
    img.save("entry.png", format="PNG")
    b = open("entry.png", "rb").read()
    assert len(b) <= 1048576, f"{len(b)} bytes > 1 MiB"
    sha = hashlib.sha256(b).hexdigest()
    # determinism: render twice, byte-identical
    img2 = render_variant("A")
    img2.save("entry-run2.png", format="PNG")
    b2 = open("entry-run2.png", "rb").read()
    assert hashlib.sha256(b2).hexdigest() == sha, "non-deterministic render"
    os.remove("entry-run2.png")
    print(f"entry.png: {len(b)} bytes sha256={sha[:16]}... deterministic OK")


if __name__ == "__main__":
    main()

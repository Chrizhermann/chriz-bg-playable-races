"""Weapon-group layers for the hobgoblin protagonist, drawn along the game's sword layer.

The hobgoblin's sword layer (MHOBS*) holds one small frame per body frame: a hilt (crossguard
and pommel in the metal range 4-15 and the fixed colours 113-127, grip in the leather range
52-63) and a blade in the armour range 64-75, widened into a smear in swing frames. Per frame
this tool measures the pommel, the grip (the hand) and the blade axis, then draws another
weapon along that axis: wood in the leather range like the sword's grip, metal in the armour
range like its blade, so the game colours them as it colours the sword. Parts that reach
beyond the sword (polearm shafts, the butt behind the hand) are left out where the body
(MHOB*) covers them, as if they passed behind it.

The pixels are this tool's own drawing; from the game it takes only where the hand is and
where the body covers, per frame. The written BAMs carry no palette (all zero): the installer
gives each the palette of the game's own sword layer.

Writes into <out>:
  <group>_<sfx>.bam   BAMC, the sword layer's cycles, identical frames stored once
  art.tpa             the groups and the frame geometry sums (hg_bam_geometry_sum) of the
                      game sprites the art was drawn for; the installer uses the art only
                      on sprites with the same geometry

usage: python -I tools/hob_weapon_art.py <game folder> <out folder> [group,...]
groups: axe halberd spear staff mace morningstar hammer club flail dagger sling (default: all)
Reads the game folder only.
"""
import math
import struct
import sys
import zlib
from pathlib import Path

METAL = range(4, 16)
LEATHER = range(52, 64)
ARMOUR = range(64, 76)
FIXED = range(113, 128)
SFX = ("G1", "G1E", "G2", "G2E")
GROUPS = ("axe", "halberd", "spear", "staff", "mace", "morningstar", "hammer", "club", "flail", "dagger", "sling")
SOURCES = [f"MHOB{s}" for s in SFX] + [f"MHOBS{s}" for s in SFX]

# palette indices: wood in the leather range, metal in the armour range (lighter = lower)
WOOD_HI, WOOD, WOOD_DARK, WOOD_CAP = 56, 58, 61, 62
MET_HI, MET_EDGE, MET, MET_DARK, MET_LINE = 64, 65, 68, 71, 73


# ---------------------------------------------------------------- game files (read only)
class Game:
    """BAM resources of an IE game folder: override first, then the KEY's BIFFs."""

    def __init__(self, root):
        self.root = Path(root)
        key = (self.root / "chitin.key").read_bytes()
        if key[:8] != b"KEY V1  ":
            raise SystemExit(f"{root}: chitin.key is no KEY V1")
        nbif, nres, bifoff, resoff = struct.unpack_from("<IIII", key, 8)
        self.bifs = []
        for i in range(nbif):
            _, off, size, _ = struct.unpack_from("<IIHH", key, bifoff + i * 12)
            self.bifs.append(key[off:off + size].rstrip(b"\0").decode("ascii").replace("\\", "/"))
        self.key = {}
        for i in range(nres):
            name, kind, loc = struct.unpack_from("<8sHI", key, resoff + i * 14)
            self.key[(name.rstrip(b"\0").decode("ascii", "replace").upper(), kind)] = loc
        ov = self.root / "override"
        self.override = {p.stem.upper(): p for p in ov.iterdir()
                         if p.is_file() and p.suffix.lower() == ".bam"} if ov.is_dir() else {}

    def bam(self, name):
        name = name.upper()
        if name in self.override:
            return self.override[name].read_bytes()
        loc = self.key.get((name, 1000))
        if loc is None:
            raise SystemExit(f"{self.root}: no {name}.BAM")
        path = self.root / self.bifs[loc >> 20]
        with path.open("rb") as s:
            head = s.read(20)
            if head[:8] != b"BIFFV1  ":
                raise SystemExit(f"{path}: not an uncompressed BIFF V1 ({head[:8]!r})")
            nfile, _, foff = struct.unpack_from("<III", head, 8)
            for i in range(nfile):
                s.seek(foff + i * 16)
                loc2, off, size, kind, _ = struct.unpack("<IIIHH", s.read(16))
                if (loc2 & 0x3FFF) == (loc & 0x3FFF) and kind == 1000:
                    s.seek(off)
                    return s.read(size)
        raise SystemExit(f"{path}: no entry for {name}.BAM")


class Frame:
    def __init__(self, w, h, cx, cy, pixels):
        self.w, self.h, self.cx, self.cy, self.pixels = w, h, cx, cy, pixels


class Bam:
    """Decoded BAM V1 (or BAMC): frames, cycles (count, first), lookup table."""

    def __init__(self, data):
        if data[:8] == b"BAMCV1  ":
            data = zlib.decompress(data[12:])
        if data[:8] != b"BAM V1  ":
            raise SystemExit(f"not a BAM V1: {data[:8]!r}")
        self.raw = data
        nfr, ncy, rle = struct.unpack_from("<HBB", data, 8)
        fo, po, lo = struct.unpack_from("<III", data, 0x0C)
        self.frames = []
        for i in range(nfr):
            w, h, cx, cy, off = struct.unpack_from("<HHhhI", data, fo + i * 12)
            n, p = w * h, off & 0x7FFFFFFF
            if off & 0x80000000:
                pix = data[p:p + n]
            else:
                out = bytearray()
                while len(out) < n:
                    b = data[p]
                    p += 1
                    if b == rle:
                        out += bytes([b]) * (data[p] + 1)
                        p += 1
                    else:
                        out.append(b)
                pix = bytes(out[:n])
            self.frames.append(Frame(w, h, cx, cy, pix))
        self.cycles = [struct.unpack_from("<HH", data, fo + nfr * 12 + i * 4) for i in range(ncy)]
        nlook = max((s + c for c, s in self.cycles), default=0)
        self.lookup = list(struct.unpack_from(f"<{nlook}H", data, lo)) if nlook else []

    def cycle_frames(self, c):
        count, start = self.cycles[c]
        return self.lookup[start:start + count]


def geometry_sums(data):
    """The installer's hg_bam_geometry_sum of a BAM (BAM V1 or BAMC bytes)."""
    if data[:8] == b"BAMCV1  ":
        data = zlib.decompress(data[12:])
    nfr, ncy = struct.unpack_from("<HB", data, 8)
    fo, _, lo = struct.unpack_from("<III", data, 0x0C)
    s1 = s2 = ncy

    def mix(v):
        nonlocal s1, s2
        s1 = (s1 * 31 + v) % 1000003
        s2 = (s2 * 37 + v) % 999983

    for c in range(ncy):
        cnt, first = struct.unpack_from("<HH", data, fo + nfr * 12 + c * 4)
        mix(cnt + 1)
        for k in range(cnt):
            (fi,) = struct.unpack_from("<H", data, lo + (first + k) * 2)
            if fi >= nfr:
                mix(7)
            else:
                w, h, cx, cy = struct.unpack_from("<HHhh", data, fo + fi * 12)
                mix(w + 11)
                mix(h + 13)
                mix(cx + 32768)
                mix(cy + 32768)
    return s1, s2


# ---------------------------------------------------------------- geometry
def measure(f):
    """Pommel, grip, unit axis toward the tip, tip and smear width of one sword frame, in
    coordinates relative to the frame's centre (the creature's anchor)."""
    blade, hilt = [], []
    for y in range(f.h):
        for x in range(f.w):
            v = f.pixels[y * f.w + x]
            if v in ARMOUR:
                blade.append((x - f.cx, y - f.cy))
            elif v in METAL or v in LEATHER or v in FIXED:
                hilt.append((x - f.cx, y - f.cy))
    if not blade and not hilt:
        return None
    if len(blade) < 3:
        return {"stub": hilt + blade}
    bx = sum(p[0] for p in blade) / len(blade)
    by = sum(p[1] for p in blade) / len(blade)
    sxx = sum((p[0] - bx) ** 2 for p in blade)
    syy = sum((p[1] - by) ** 2 for p in blade)
    sxy = sum((p[0] - bx) * (p[1] - by) for p in blade)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(ang), math.sin(ang)
    if hilt:
        hx = sum(p[0] for p in hilt) / len(hilt)
        hy = sum(p[1] for p in hilt) / len(hilt)
        if (bx - hx) * ux + (by - hy) * uy < 0:
            ux, uy = -ux, -uy
    elif bx * ux + (by + 30) * uy < 0:
        # no hilt seen: point away from the upper body
        ux, uy = -ux, -uy
    nx, ny = -uy, ux
    ts = [(p[0] - bx) * ux + (p[1] - by) * uy for p in blade]
    ss = [(p[0] - bx) * nx + (p[1] - by) * ny for p in blade]
    tip_t, base_t = max(ts), min(ts)
    tip = (bx + ux * tip_t, by + uy * tip_t)
    base = (bx + ux * base_t, by + uy * base_t)
    if hilt:
        back = min(hilt, key=lambda p: (p[0] - bx) * ux + (p[1] - by) * uy)
        pt = (back[0] - bx) * ux + (back[1] - by) * uy
        pommel = (bx + ux * pt, by + uy * pt)
        grip = (hx, hy)
    else:
        pommel = grip = base
    return {"pommel": pommel, "grip": grip, "base": base, "tip": tip, "u": (ux, uy), "n": (nx, ny),
            "width": max(ss) - min(ss) + 1, "count": len(blade)}


def body_mask(f):
    """Body pixels (not transparent, not shadow) relative to the anchor."""
    return {(x - f.cx, y - f.cy) for y in range(f.h) for x in range(f.w) if f.pixels[y * f.w + x] > 1}


# ---------------------------------------------------------------- drawing
class Canvas:
    def __init__(self, mask=frozenset()):
        self.px = {}
        self.mask = mask

    def put(self, x, y, v, over=True, behind=False):
        k = (int(round(x)), int(round(y)))
        if behind and k in self.mask:
            return
        if over or k not in self.px:
            self.px[k] = v

    def line(self, a, b, v, over=True, behind=False):
        x0, y0 = int(round(a[0])), int(round(a[1]))
        x1, y1 = int(round(b[0])), int(round(b[1]))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, v, over, behind)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def shape(self, pts, fill, line, edge=None, edge_test=None, behind=False):
        """Filled polygon with a dark outline and an optional light edge just inside it."""
        inside = cells(pts)
        for (x, y) in inside:
            border = any((x + dx, y + dy) not in inside for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            v = line if border else (edge if edge is not None and edge_test(x, y) else fill)
            if behind and (x, y) in self.mask:
                continue
            self.px[(x, y)] = v
        return inside


def point_in(pts, x, y):
    c = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
    return c


def cells(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    out = set()
    for y in range(int(math.floor(min(ys))) - 1, int(math.ceil(max(ys))) + 2):
        for x in range(int(math.floor(min(xs))) - 1, int(math.ceil(max(xs))) + 2):
            if point_in(pts, x, y):
                out.add((x, y))
    return out


def frm(o, g, t, s):
    """Point at distance t along the weapon axis from origin o, side offset s."""
    (ux, uy), (nx, ny) = g["u"], g["n"]
    return (o[0] + ux * t + nx * s, o[1] + uy * t + ny * s)


def side_of(g, o, t):
    """+1 or -1: the side facing away from the upper body (about 30 px above the anchor)."""
    hx, hy = frm(o, g, t, 0)
    nx, ny = g["n"]
    return 1 if hx * nx + (hy + 30) * ny >= 0 else -1


def span(g):
    """Visible sword length from the pommel to the tip, and from the grip to the tip."""
    return max(4.0, math.dist(g["pommel"], g["tip"])), max(3.0, math.dist(g["grip"], g["tip"]))


def shaft(c, g, o, t0, t1, colour, dark=None, side=1, vis=None):
    """Wooden shaft from t0 to t1 along the axis from o; beyond vis (and behind the hand,
    t < 0) it passes behind the body. A point every half pixel, so a shaft of any length has
    no gaps (a fixed 41 points left every other pixel out of polearms: lab run 15)."""
    n = max(2, int(math.ceil(2 * abs(t1 - t0))))
    for k in range(n + 1):
        t = t0 + (t1 - t0) * k / n
        p = frm(o, g, t, 0)
        c.put(p[0], p[1], colour, True, t < 0 or (vis is not None and t > vis))
    if dark is not None and abs(t1 - t0) >= 12:
        # a dark edge along one side, leaving a twentieth of the shaft free at each end
        for k in range(int(math.ceil(0.05 * n)), int(math.floor(0.95 * n)) + 1):
            t = t0 + (t1 - t0) * k / n
            q = frm(o, g, t, -side * 0.9)
            c.put(q[0], q[1], dark, False, t < 0 or (vis is not None and t > vis))


def smear(c, g, o, t0, t1, s_edge, side):
    """Swing frames: the sword is drawn wide; trail the head's edge across that width."""
    if g["width"] >= 4:
        for k in range(1, int(g["width"] // 2)):
            c.line(frm(o, g, t0, s_edge - side * k), frm(o, g, t1, s_edge - side * k), MET_DARK, over=False)


def side_dist(g, o, side):
    (nx, ny) = g["n"]
    return lambda x, y: ((x - o[0]) * nx + (y - o[1]) * ny) * side


def side_dist_test(g, o, side, limit):
    sd = side_dist(g, o, side)
    return lambda x, y: sd(x, y) >= limit


def blob(c, centre, r, fill, line, hi=None):
    pts = [(centre[0] + r * math.cos(a * math.pi / 8), centre[1] + r * math.sin(a * math.pi / 8)) for a in range(16)]
    inside = c.shape(pts, fill, line)
    if hi is not None and r >= 2:
        c.put(centre[0] - 0.6, centre[1] - 0.6, hi)
    return inside


# ---------------------------------------------------------------- weapon recipes
def draw_axe(g, c):
    p = g["pommel"]
    full, _ = span(g)
    L = 0.85 * full
    side = side_of(g, p, L)
    hh = min(11.0, max(4.0, 0.36 * L))
    hw = min(8.0, max(3.5, 0.27 * L))
    shaft(c, g, p, 0, L, WOOD, WOOD_DARK, side)
    tt = [(-0.05, 0.5), (0.10, 0.55), (0.18, 1.0), (-0.45, 1.15), (-1.05, 1.0), (-0.65, 0.55), (-0.55, 0.5)]
    pts = [frm(p, g, L + a * hh, side * (b * hw if b > 0.6 else b)) for a, b in tt]
    sd = side_dist(g, p, side)
    inside = cells(pts)
    edge_s = max((sd(x, y) for x, y in inside), default=0)
    c.shape(pts, MET, MET_LINE, MET_EDGE, lambda x, y: sd(x, y) >= edge_s - 1.6)
    smear(c, g, p, L - 1.05 * hh, L + 0.18 * hh, side * hw, side)
    c.put(*frm(p, g, 0, 0), WOOD_CAP)


def draw_halberd(g, c):
    q = g["grip"]
    _, reach = span(g)
    top = 1.45 * reach
    butt = -0.55 * reach
    side = side_of(g, q, top)
    shaft(c, g, q, butt, top, WOOD, WOOD_DARK, side, vis=reach)
    hh = min(10.0, max(4.0, 0.30 * reach))
    hw = min(7.0, max(3.0, 0.24 * reach))
    base = top - 0.25 * hh
    blade = [frm(q, g, base + a * hh, side * (b * hw if b > 0.6 else b)) for a, b in
             [(0.05, 0.5), (0.15, 1.0), (-0.55, 1.1), (-1.0, 0.9), (-0.75, 0.5)]]
    sd = side_dist(g, q, side)
    inside = cells(blade)
    edge_s = max((sd(x, y) for x, y in inside), default=0)
    beyond = top > reach
    c.shape(blade, MET, MET_LINE, MET_EDGE, lambda x, y: sd(x, y) >= edge_s - 1.4, behind=beyond)
    # back spike and top spike
    c.shape([frm(q, g, base - 0.55 * hh, -side * 0.4), frm(q, g, base - 0.35 * hh, -side * 0.65 * hw),
             frm(q, g, base - 0.15 * hh, -side * 0.4)], MET, MET_LINE, behind=beyond)
    tip = min(6.0, max(2.0, 0.18 * reach))
    c.line(frm(q, g, top, 0), frm(q, g, top + tip, 0), MET_EDGE, True, beyond)
    smear(c, g, q, base - 1.0 * hh, base + 0.15 * hh, side * hw, side)


def draw_spear(g, c):
    q = g["grip"]
    _, reach = span(g)
    top = 1.5 * reach
    butt = -0.6 * reach
    shaft(c, g, q, butt, top, WOOD, WOOD_DARK, 1, vis=reach)
    hl = min(9.0, max(3.5, 0.30 * reach))
    hw = min(2.6, max(1.2, 0.08 * reach))
    head = [frm(q, g, top - 0.8, -0.6), frm(q, g, top + 0.35 * hl, -hw), frm(q, g, top + hl, 0),
            frm(q, g, top + 0.35 * hl, hw), frm(q, g, top - 0.8, 0.6)]
    beyond = top > reach
    c.shape(head, MET, MET_LINE, MET_EDGE, lambda x, y: False, behind=beyond)
    c.line(frm(q, g, top, 0), frm(q, g, top + 0.8 * hl, 0), MET_HI, True, beyond)


def draw_staff(g, c):
    q = g["grip"]
    _, reach = span(g)
    top = 1.15 * reach
    butt = -0.85 * reach
    shaft(c, g, q, butt, top, WOOD_HI, WOOD_DARK, 1, vis=reach)
    # darker capped ends
    for t0, t1 in ((top - 1.5, top), (butt, butt + 1.5)):
        c.line(frm(q, g, t0, 0), frm(q, g, t1, 0), WOOD_CAP, True, t1 > reach or t0 < 0)


def draw_mace(g, c, spikes=False):
    p = g["pommel"]
    full, _ = span(g)
    L = 0.8 * full
    shaft(c, g, p, 0, L, WOOD, WOOD_DARK)
    r = min(4.0, max(1.6, 0.13 * L))
    centre = frm(p, g, L + 0.4 * r, 0)
    blob(c, centre, r, MET, MET_LINE, MET_HI)
    if spikes:
        for a in range(8):
            ang = a * math.pi / 4 + math.pi / 8
            c.put(centre[0] + (r + 1.2) * math.cos(ang), centre[1] + (r + 1.2) * math.sin(ang), MET_EDGE, False)
    else:
        # flanges: short ridges along the head
        c.line(frm(centre, g, -r, 0), frm(centre, g, r, 0), MET_EDGE)
    c.put(*frm(p, g, 0, 0), WOOD_CAP)


def draw_morningstar(g, c):
    draw_mace(g, c, spikes=True)


def draw_hammer(g, c):
    p = g["pommel"]
    full, _ = span(g)
    L = 0.82 * full
    side = side_of(g, p, L)
    shaft(c, g, p, 0, L + 1, WOOD, WOOD_DARK, side)
    hh = min(5.0, max(2.5, 0.16 * L))
    hw = min(5.0, max(2.5, 0.17 * L))
    face = [frm(p, g, L - hh / 2, side * 0.4), frm(p, g, L - hh / 2, side * hw), frm(p, g, L + hh / 2, side * hw),
            frm(p, g, L + hh / 2, side * 0.4)]
    c.shape(face, MET, MET_LINE, MET_EDGE, side_dist_test(g, p, side, hw - 1.0))
    c.shape([frm(p, g, L - hh / 3, -side * 0.4), frm(p, g, L, -side * hw * 0.9), frm(p, g, L + hh / 3, -side * 0.4)],
            MET, MET_LINE)
    smear(c, g, p, L - hh / 2, L + hh / 2, side * hw, side)
    c.put(*frm(p, g, 0, 0), WOOD_CAP)


def draw_club(g, c):
    p = g["pommel"]
    full, _ = span(g)
    L = 0.82 * full
    w0, w1 = 0.6, min(3.2, max(1.4, 0.10 * L))
    body = [frm(p, g, 0, -w0), frm(p, g, L, -w1), frm(p, g, L + 1.2, 0), frm(p, g, L, w1), frm(p, g, 0, w0)]
    c.shape(body, WOOD, WOOD_CAP, WOOD_HI, lambda x, y: False)
    c.line(frm(p, g, 0.25 * L, 0), frm(p, g, 0.9 * L, 0), WOOD_HI, True)


def draw_flail(g, c):
    p = g["pommel"]
    full, _ = span(g)
    L = 0.45 * full
    side = side_of(g, p, L)
    shaft(c, g, p, 0, L, WOOD, WOOD_DARK, side)
    links = 3
    end = 0.78 * full
    for k in range(1, links + 1):
        t = L + (end - L) * k / (links + 1)
        c.put(*frm(p, g, t, side * 0.8 * math.sin(k * 0.9)), MET_EDGE)
    r = min(3.5, max(2.0, 0.12 * full))
    centre = frm(p, g, end + r * 0.6, side * 0.8)
    blob(c, centre, r, MET, MET_LINE, MET_HI)
    for a in range(6):
        ang = a * math.pi / 3
        c.put(centre[0] + (r + 1.1) * math.cos(ang), centre[1] + (r + 1.1) * math.sin(ang), MET_EDGE, False)
    c.put(*frm(p, g, 0, 0), WOOD_CAP)


def draw_dagger(g, c):
    p = g["pommel"]
    full, _ = span(g)
    grip_len = max(2.0, 0.17 * full)
    L = max(5.0, 0.5 * full)
    c.line(frm(p, g, 0, 0), frm(p, g, grip_len, 0), WOOD_DARK)
    guard = max(1.5, 0.07 * full)
    c.line(frm(p, g, grip_len, -guard), frm(p, g, grip_len, guard), MET_DARK)
    bw = max(0.7, 0.05 * full)
    blade = [frm(p, g, grip_len + 0.5, -bw), frm(p, g, L, 0), frm(p, g, grip_len + 0.5, bw)]
    c.shape(blade, MET, MET_LINE, MET_EDGE, lambda x, y: False)
    c.line(frm(p, g, grip_len + 1, 0), frm(p, g, L - 1, 0), MET_EDGE)


def draw_sling(g, c):
    q = g["grip"]
    _, reach = span(g)
    L = min(9.0, max(3.0, 0.45 * reach))
    side = side_of(g, q, L)
    # two cords from the hand to a small pouch
    for s in (-0.6, 0.6):
        c.line(frm(q, g, 0, s), frm(q, g, L, s + side * 0.8), WOOD_DARK)
    blob(c, frm(q, g, L + 1.2, side * 0.8), 1.4, WOOD, WOOD_CAP)


RECIPES = {"axe": draw_axe, "halberd": draw_halberd, "spear": draw_spear, "staff": draw_staff,
           "mace": draw_mace, "morningstar": draw_morningstar, "hammer": draw_hammer, "club": draw_club,
           "flail": draw_flail, "dagger": draw_dagger, "sling": draw_sling}


def draw(group, g, mask):
    c = Canvas(mask)
    if "stub" in g:
        for (x, y) in g["stub"]:
            c.put(x, y, WOOD)
        return c
    RECIPES[group](g, c)
    return c


# ---------------------------------------------------------------- BAM writing
def to_frame(canvas):
    if not canvas.px:
        return Frame(1, 1, 0, 0, b"\0")
    xs = [k[0] for k in canvas.px]
    ys = [k[1] for k in canvas.px]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    pix = bytearray(w * h)
    for (x, y), v in canvas.px.items():
        pix[(y - y0) * w + (x - x0)] = v
    return Frame(w, h, -x0, -y0, bytes(pix))


def write_bam(cycles):
    """BAMC of a BAM V1 without palette (all zero): cycles = lists of frames (None = no frame,
    65535 in the lookup table); identical frames stored once, uncompressed."""
    frames, index, lookup, cyc = [], {}, [], []
    for fl in cycles:
        cyc.append((len(fl), len(lookup)))
        for f in fl:
            if f is None:
                lookup.append(0xFFFF)
                continue
            key = (f.w, f.h, f.cx, f.cy, f.pixels)
            if key not in index:
                index[key] = len(frames)
                frames.append(f)
            lookup.append(index[key])
    nfr, ncy = len(frames), len(cyc)
    fo = 0x18
    po = fo + 12 * nfr + 4 * ncy
    lo = po + 1024
    data_off = lo + 2 * len(lookup)
    out = bytearray(b"BAM V1  " + struct.pack("<HBB", nfr, ncy, 0) + struct.pack("<III", fo, po, lo))
    blob_ = bytearray()
    for f in frames:
        out += struct.pack("<HHhhI", f.w, f.h, f.cx, f.cy, (data_off + len(blob_)) | 0x80000000)
        blob_ += f.pixels
    for count, start in cyc:
        out += struct.pack("<HH", count, start)
    out += bytes(1024)
    out += struct.pack(f"<{len(lookup)}H", *lookup)
    out += blob_
    return b"BAMCV1  " + struct.pack("<I", len(out)) + zlib.compress(bytes(out), 9)


def generate(game, group):
    """{sfx: BAMC bytes} for one weapon group."""
    out = {}
    for sfx in SFX:
        sword = Bam(game.bam(f"MHOBS{sfx}"))
        body = Bam(game.bam(f"MHOB{sfx}"))
        geo, masks, cycles = {}, {}, []
        for c in range(len(sword.cycles)):
            sf = sword.cycle_frames(c)
            bf = body.cycle_frames(c) if c < len(body.cycles) else []
            fl = []
            for k, fi in enumerate(sf):
                if fi >= len(sword.frames):
                    fl.append(None)   # the source's "no frame" entry stays one
                    continue
                if fi not in geo:
                    geo[fi] = measure(sword.frames[fi])
                g = geo[fi]
                if g is None:
                    fl.append(Frame(1, 1, 0, 0, b"\0"))
                    continue
                bi = bf[k % len(bf)] if bf else None
                if bi is not None and bi < len(body.frames) and bi not in masks:
                    masks[bi] = body_mask(body.frames[bi])
                fl.append(to_frame(draw(group, dict(g), masks.get(bi, frozenset()))))
            cycles.append(fl)
        out[sfx] = write_bam(cycles)
    return out


def manifest(game, groups):
    lines = ["// Written by tools/hob_weapon_art.py; do not edit (run the tool again instead).",
             "// The weapon groups drawn in this folder, and the frame geometry (hg_bam_geometry_sum) of",
             "// the game sprites the art was drawn for: the installer uses the art only on sprites with",
             "// the same geometry.",
             f"OUTER_SPRINT hg_art_groups ~{' '.join(groups)}~"]
    for n in (1, 2):
        lines.append(f"ACTION_DEFINE_ASSOCIATIVE_ARRAY hg_art_geo{n} BEGIN")
        for res in SOURCES:
            lines.append(f"  {res} => {geometry_sums(game.bam(res))[n - 1]}")
        lines.append("END")
    return "\r\n".join(lines) + "\r\n"


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    game = Game(sys.argv[1])
    out = Path(sys.argv[2])
    groups = sys.argv[3].split(",") if len(sys.argv) == 4 else list(GROUPS)
    for group in groups:
        if group not in RECIPES:
            raise SystemExit(f"unknown group {group}; known: {', '.join(GROUPS)}")
    out.mkdir(parents=True, exist_ok=True)
    for group in groups:
        for sfx, data in generate(game, group).items():
            (out / f"{group}_{sfx.lower()}.bam").write_bytes(data)
        print("written", group)
    (out / "art.tpa").write_bytes(manifest(game, groups).encode("ascii"))
    print("written art.tpa")


if __name__ == "__main__":
    main()

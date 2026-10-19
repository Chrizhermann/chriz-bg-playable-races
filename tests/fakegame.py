"""Synthetic game folders and file builders for the offline WeiDU tests.

A fake game is a chitin.key indexing one BIFF, a dialog.tlk and an override folder, just
enough for WeiDU to run real COPY_EXISTING/APPEND/uninstall paths. All data is made up
here; no game files are read or needed.
"""
import hashlib
import os
import shutil
import struct
import subprocess
from pathlib import Path

# CBPR_TEST_LIB tests another copy of the library (e.g. a deliberately broken one).
LIB = Path(os.environ.get("CBPR_TEST_LIB")
           or Path(__file__).resolve().parents[1] / "chriz-bg-playable-races" / "lib" / "hg_functions.tpa")
# The EE Soundset Tool helper the library calls, as the mod ships it.
TPH = Path(__file__).resolve().parents[1] / "chriz-bg-playable-races" / "lib" / "cd_add_soundset.tph"
# The race library (CBPR_TEST_RACE_LIB: another copy), and the race hook's files it installs.
RACE_LIB = Path(os.environ.get("CBPR_TEST_RACE_LIB")
                or Path(__file__).resolve().parents[1] / "chriz-bg-playable-races" / "lib" / "race_functions.tpa")
RACE_DIR = Path(__file__).resolve().parents[1] / "chriz-bg-playable-races" / "race"

TP2_HEAD = r"""BACKUP ~cbprtest/backup~
AUTHOR ~test~
ALWAYS
  INCLUDE ~cbprtest/hg_functions.tpa~
  INCLUDE ~cbprtest/race_functions.tpa~
  INCLUDE ~cbprtest/cd_add_soundset.tph~
END
BEGIN ~test~ DESIGNATED 0
"""

# Areas WeiDU's GAME_IS looks for (EET also has override/eet.flag).
GAME_MARKERS = {"bgee": ["OH1000"], "sod": ["OH1000", "BD0100"], "bg2ee": ["OH6000"], "eet": ["OH1000", "OH6000"]}

TYPES = {"2DA": 1012, "ARE": 1010, "BAM": 1000, "BCS": 1007, "CRE": 1009, "IDS": 1008, "ITM": 1005, "MENU": 1032, "WAV": 4}


def make_tlk(entries):
    """TLK V1 from (text, sound) pairs; entry 0 is normally the empty string."""
    head = 18 + 26 * len(entries)
    table, blob = bytearray(), bytearray()
    for text, sound in entries:
        data = text.encode("utf-8")
        flags = (1 if data else 0) | (2 if sound else 0)
        table += struct.pack("<H8sIIII", flags, sound.encode("ascii"), 0, 0, len(blob), len(data))
        blob += data
    return b"TLK V1  " + struct.pack("<HII", 0, len(entries), head) + table + blob


def tlk_entries(data):
    assert data[:8] == b"TLK V1  "
    count, start = struct.unpack_from("<II", data, 10)
    out = []
    for i in range(count):
        e = 18 + 26 * i
        sound = data[e + 2:e + 10].split(b"\0", 1)[0].decode("ascii").upper()
        off, ln = struct.unpack_from("<II", data, e + 18)
        out.append((data[start + off:start + off + ln].decode("utf-8"), sound))
    return out


def make_2da(columns, rows, default="-1"):
    """rows: list of (label, [values]). Columns are padded like the games' own tables."""
    pad = lambda v: v.ljust(max(10, len(v) + 1))  # noqa: E731  (always at least one space)
    out = ["2DA V1.0", default, " " * 10 + "".join(pad(c) for c in columns)]
    out += [pad(label) + "".join(pad(v) for v in values) for label, values in rows]
    return ("\r\n".join(out) + "\r\n").encode("ascii")


def table(data):
    rows = [ln.split() for ln in data.decode("latin-1").splitlines()]
    return rows[2], {r[0]: r[1:] for r in rows[3:] if r}


def make_cre(anim, sounds, size=0x2D4):
    """CRE V1.0 with animation `anim` and soundset slots {slot: strref} (others -1)."""
    b = bytearray(size)
    b[0:8] = b"CRE V1.0"
    struct.pack_into("<I", b, 0x28, anim)
    for slot in range(100):
        if 0xA4 + slot * 4 + 4 <= size:
            struct.pack_into("<i", b, 0xA4 + slot * 4, sounds.get(slot, -1))
    return bytes(b)


def make_itm(itype, code, size=0x72, sig=b"ITM V1  "):
    """ITM V1 header of item type `itype` (ITM 0x1c) with look code `code` (bytes, ITM 0x22)."""
    b = bytearray(size)
    b[0:8] = sig
    struct.pack_into("<H", b, 0x1C, itype)
    b[0x22:0x24] = code
    return bytes(b)


def rle_encode(pixels, index):
    out, i = bytearray(), 0
    while i < len(pixels):
        if pixels[i] == index:
            n = 1
            while i + n < len(pixels) and pixels[i + n] == index and n < 256:
                n += 1
            out += bytes([index, n - 1])
            i += n
        else:
            out.append(pixels[i])
            i += 1
    return bytes(out)


def make_bam(frames, cycles, palette, rle_index=0, compressed=False):
    """BAM V1 (or BAMC). frames: (w, h, cx, cy, pixels, rle); cycles: lists of frame indices."""
    fo = 0x18
    co = fo + 12 * len(frames)
    po = co + 4 * len(cycles)
    lo = po + 1024
    lookup = [f for c in cycles for f in c]
    do = lo + 2 * len(lookup)
    head = bytearray(b"BAM V1  " + struct.pack("<HBBIII", len(frames), len(cycles), rle_index, fo, po, lo))
    entries, data = bytearray(), bytearray()
    for w, h, cx, cy, pixels, rle in frames:
        payload = rle_encode(pixels, rle_index) if rle else pixels
        entries += struct.pack("<HHhhI", w, h, cx, cy, (do + len(data)) | (0 if rle else 0x80000000))
        data += payload
    first = 0
    for c in cycles:
        entries += struct.pack("<HH", len(c), first)
        first += len(c)
    bam = bytes(head + entries + palette + struct.pack(f"<{len(lookup)}H", *lookup) + data)
    if compressed:
        import zlib
        return b"BAMCV1  " + struct.pack("<I", len(bam)) + zlib.compress(bam)
    return bam


def read_bam(data):
    """Decoded BAM V1: frames (w, h, cx, cy, pixels), cycles (count, first), lookup, palette."""
    assert data[:8] == b"BAM V1  ", data[:8]
    nfr, ncy, rle = struct.unpack_from("<HBB", data, 8)
    fo, po, lo = struct.unpack_from("<III", data, 0x0C)
    frames = []
    for i in range(nfr):
        w, h, cx, cy, off = struct.unpack_from("<HHhhI", data, fo + 12 * i)
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
        frames.append((w, h, cx, cy, pix))
    cycles = [struct.unpack_from("<HH", data, fo + 12 * nfr + 4 * i) for i in range(ncy)]
    nlook = max((c + f for c, f in cycles), default=0)
    lookup = list(struct.unpack_from(f"<{nlook}H", data, lo))
    return frames, cycles, lookup, data[po:po + 1024]


# EEex as the race component checks for it: its M_ file, the hook functions in its Lua files, the
# pattern folder and the trigger the world scripts use. Only the lines the installer looks at.
EEEX_LUA = {
    "EEex_scripts/EEex_Assembly_x86-64.lua": "function EEex_HookShimFunctionMaintainOriginal(address, restoreSize, originalLabel, assembly)",
    "EEex_scripts/EEex_Assembly.lua": "function EEex_LabelDefault(label, default)",
    "EEex_scripts/EEex_GameState.lua": "function EEex_GameState_AddInitializedListener(listener)",
    "EEex_scripts/EEex_Menu.lua": "function EEex_Menu_AddAfterMainFileLoadedListener(listener)",
    "EEex_scripts/EEex_Resource.lua": "function EEex_Resource_Load2DA(resref)",
}
EEEX_TRIGGERS = ["0x400F Global(S:Name*,S:Area*,I:Value*)", "0x410E EEex_LuaTrigger(S:Chunk*)"]


def eeex_files(trigger=True, functions=True):
    """Files of a fake EEex install: {path under the game folder: bytes}."""
    out = {"override/M___EEex.lua": b"if not EEex_Active then error('EEex not active') end\r\n",
           "EEex_scripts/extra_pattern_dbs/v2.7.3.0.db": b"[Some-Label]\r\nPattern=90\r\n"}
    if functions:
        out.update({k: (v + "\r\nend\r\n").encode("ascii") for k, v in EEEX_LUA.items()})
    lines = EEEX_TRIGGERS if trigger else EEEX_TRIGGERS[:1]
    out["override/TRIGGER.IDS"] = ("IDS V1.0\r\n" + "\r\n".join(lines) + "\r\n").encode("ascii")
    return out


def write_key_bif(root, resources):
    name = b"data/fixture.bif\0"
    data_offset = 20 + 16 * len(resources)
    entries, contents = bytearray(), bytearray()
    for ordinal, (_, kind, data) in enumerate(resources):
        entries += struct.pack("<IIIHH", ordinal, data_offset + len(contents), len(data), kind, 0)
        contents += data
    bif = b"BIFFV1  " + struct.pack("<III", len(resources), 0, 20) + entries + contents
    key = bytearray(b"KEY V1  " + struct.pack("<IIII", 1, len(resources), 24, 36 + len(name)))
    key += struct.pack("<IIHH", len(bif), 36, len(name), 1) + name
    for ordinal, (resref, kind, _) in enumerate(resources):
        key += struct.pack("<8sHI", resref.encode("ascii"), kind, ordinal)
    (root / "data").mkdir()
    (root / "data/fixture.bif").write_bytes(bif)
    (root / "chitin.key").write_bytes(key)


class FakeGame:
    """A fresh fake game folder (BG2:EE unless `game` names bgee, sod or eet).
    biff/override: {"NAME.EXT": bytes}."""

    def __init__(self, root, weidu, tp2_body, tlk=None, biff=None, override=None, sounds_folder=True,
                 game="bg2ee", files=None):
        self.root, self.weidu = Path(root), weidu
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "override").mkdir(parents=True)
        (self.root / "lang/en_us").mkdir(parents=True)
        (self.root / "lang/en_us/dialog.tlk").write_bytes(tlk or make_tlk([("", "")]))
        if sounds_folder:
            (self.root / "lang/en_us/sounds").mkdir()
        (self.root / "cbprtest").mkdir()
        shutil.copy(LIB, self.root / "cbprtest/hg_functions.tpa")
        shutil.copy(RACE_LIB, self.root / "cbprtest/race_functions.tpa")
        shutil.copy(TPH, self.root / "cbprtest/cd_add_soundset.tph")
        shutil.copytree(RACE_DIR, self.root / "chriz-bg-playable-races/race")
        (self.root / "cbprtest/setup-cbprtest.tp2").write_text(TP2_HEAD + tp2_body, encoding="ascii")
        if game == "eet":
            (self.root / "override/eet.flag").write_bytes(b"EET")
        resources = [(m, TYPES["ARE"], b"AREAV1.0") for m in GAME_MARKERS[game]]
        for name, data in (biff or {}).items():
            stem, ext = name.rsplit(".", 1)
            resources.append((stem, TYPES[ext.upper()], data))
        write_key_bif(self.root, resources)
        for name, data in (override or {}).items():
            (self.root / "override" / name).write_bytes(data)
        for rel, data in (files or {}).items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(data)

    def run(self, action="--force-install-list"):
        out = subprocess.run([self.weidu, "cbprtest/setup-cbprtest.tp2", "--no-auto-tp2", "--noautoupdate",
                              "--game", str(self.root), "--language", "0", "--use-lang", "en_US", action, "0",
                              "--no-exit-pause", "--log", f"weidu{action}.debug"], cwd=self.root,
                             stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        text = (out.stdout + out.stderr).decode("utf-8", "replace")
        (self.root / f"weidu{action}.transcript").write_text(text, encoding="utf-8")
        return text

    def install(self):
        return self.run("--force-install-list")

    def uninstall(self):
        return self.run("--force-uninstall-list")

    def results(self, out, tag):
        """Values of the test's `PRINT ~RESULT <tag> ...~` lines."""
        prefix = f"RESULT {tag} "
        return [ln[len(prefix):].strip() for ln in out.splitlines() if ln.startswith(prefix)]

    def override(self, rel="override"):
        """Hashes of the files under `rel` (the override folder by default)."""
        return {p.relative_to(self.root).as_posix().lower(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root / rel).rglob("*") if p.is_file()}

    def tree(self):
        """Hashes of every game file apart from the test mod (with the race hook's source files),
        WeiDU's logs and dialog.tlk (WeiDU keeps appended strings on uninstall)."""
        out = {}
        for p in self.root.rglob("*"):
            rel = p.relative_to(self.root).as_posix().lower()
            if p.is_file() and not (rel.startswith(("cbprtest/", "weidu", "chriz-bg-playable-races/"))
                                    or rel.endswith("dialog.tlk")):
                out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    def game_files(self):
        """Hashes of everything an install may touch: override and lang folders."""
        return {**self.override(), **self.override("lang")}

    def read(self, rel):
        return (self.root / rel).read_bytes()


def installed_ok(out):
    return "SUCCESSFULLY INSTALLED" in out or "INSTALLED WITH WARNINGS" in out


def failed(out):
    return "NOT INSTALLED DUE TO ERRORS" in out

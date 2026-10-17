"""Offline tests for the installer library: real WeiDU runs in small synthetic game folders,
no game installation or game files needed (all test data is made up in fakegame.py).

usage: python tests/run_tests.py --weidu <path to weidu.exe or a mod's setup-*.exe> [--keep DIR]
Exit code 0 when every test passes.
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fakegame as fg  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MOD = REPO / "chriz-bg-playable-races"
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


# --- CAMPAIGN.2DA: which world scripts the campaigns run -------------------------------

WS_TP2 = r"""COPY_EXISTING - ~campaign.2da~ ~override~
  CLEAR_ARRAY ws
  LPF hg_campaign_world_scripts RET_ARRAY ws = scripts END
  SPRINT found ~~
  PHP_EACH ws AS k => v BEGIN SPRINT found ~%found% %k%~ END
  PATCH_PRINT ~RESULT WS [%found%]~
"""


@test
def world_scripts(work, weidu):
    """The WORLDSCRIPT column is found wherever it is (also twice, as in EET); names are
    upper-cased and listed once; "*" rows are skipped; no column means no scripts."""
    cases = {
        "repeated_column": (["WORLDSCRIPT", "DESCRIPTION", "SAVE_DIR", "WORLDSCRIPT", "KEEP_POWERS"],
                            [("SOA", ["BALDUR", "-1", "save", "BALDUR", "1"]),
                             ("TOB", ["BALDUR25", "-1", "save", "BALDUR25", "0"]),
                             ("SOD", ["BDBALDUR", "-1", "save", "BDBALDUR", "1"]),
                             ("TUT", ["baldur", "-1", "save", "baldur", "0"])], {"BALDUR", "BALDUR25", "BDBALDUR"}),
        "moved_column": (["DESCRIPTION", "WORLDSCRIPT", "SAVE_DIR"],
                         [("SOA", ["-1", "BALDUR", "save"]), ("TOB", ["-1", "BALDUR25", "save"])],
                         {"BALDUR", "BALDUR25"}),
        "star_row": (["WORLDSCRIPT", "SAVE_DIR", "ICON"], [("A", ["*", "save", "1"]), ("B", ["BALDUR", "save", "2"])],
                     {"BALDUR"}),
        "no_column": (["DESCRIPTION", "SAVE_DIR", "ICON"], [("A", ["-1", "save", "1"])], set()),
        # With one or two columns WeiDU counts the "2DA V1.0" line among the rows as well.
        "two_columns": (["SAVE_DIR", "WORLDSCRIPT"], [("A", ["save", "BALDUR"]), ("B", ["save", "BALDUR25"])],
                        {"BALDUR", "BALDUR25"}),
        "one_column": (["WORLDSCRIPT"], [("A", ["BALDUR"]), ("B", ["BDBALDUR"])], {"BALDUR", "BDBALDUR"}),
    }
    fails = []
    for name, (cols, rows, want) in cases.items():
        g = fg.FakeGame(work / f"ws_{name}", weidu, WS_TP2, biff={"CAMPAIGN.2DA": fg.make_2da(cols, rows, "*")})
        out = g.install()
        got = g.results(out, "WS")
        if not fg.installed_ok(out) or len(got) != 1 or set(got[0].strip("[]").split()) != want:
            fails.append(f"{name}: {got}, want {sorted(want)}")
    return fails


# --- The ability block on top of the world scripts -------------------------------------

# Just the IDS entries the scripts use, with the EE games' signatures.
SCRIPT_IDS = {
    "TRIGGER.IDS": ["0x400F Global(S:Name*,S:Area*,I:Value*)", "0x4037 StateCheck(O:Object*,I:State*State)",
                    "0x4043 InParty(O:Object*)", "0x40E2 CheckSpellState(O:Object*,I:State*splstate)"],
    "ACTION.IDS": ["30 SetGlobal(S:Name*,S:Area*,I:Value*)", "36 Continue()", "160 ApplySpellRES(S:RES*,O:Target)"],
    "OBJECT.IDS": ["0 Nothing", "1 Myself", "21 Player1"],
    "STATE.IDS": ["0x00000FC0 STATE_REALLY_DEAD"],
}
OTHER_BLOCK = """IF
  Global("OTHER_MOD_{n}","GLOBAL",0)
THEN
  RESPONSE #100
    SetGlobal("OTHER_MOD_{n}","GLOBAL",1)
END
"""
GIVE_BAF = MOD / "hobgoblin/give_ability.baf"
EW_TP2 = r"""OUTER_SET hg_splstate = 195
LAF hg_extend_world_scripts STR_VAR baf = ~cbprtest/give_ability.baf~ RET count END
PRINT ~RESULT EW %count%~
"""


def script_ids():
    return {name: ("IDS V1.0\r\n" + "\r\n".join(lines) + "\r\n").encode() for name, lines in SCRIPT_IDS.items()}


def compile_bafs(work, weidu, bafs):
    """{name: BAF text} compiled by WeiDU: ({name: BCS bytes} or None, WeiDU output)."""
    g = fg.FakeGame(work / "ew_compile", weidu, "".join(f"COMPILE ~cbprtest/{n}.baf~\n" for n in bafs),
                    biff=script_ids())
    for n, text in bafs.items():
        (g.root / f"cbprtest/{n}.baf").write_text(text, encoding="ascii")
    out = g.install()
    if not fg.installed_ok(out) or "ERROR" in out:
        return None, out
    return {n: g.read(f"override/{n}.bcs") for n in bafs}, out


def find_ci(folder, name):
    """The one file in `folder` called `name` in any letter case, else None."""
    hits = [p for p in folder.iterdir() if p.name.lower() == name.lower()]
    return hits[0] if len(hits) == 1 else None


@test
def world_script_extension(work, weidu):
    """The shipped give_ability.baf, its marker state filled in, goes on top of each world
    script the campaigns run (once, also when named twice), in front of the blocks already
    there; named scripts the game lacks are skipped and other scripts stay as they are;
    BALDUR.BCS without a CAMPAIGN.2DA; uninstall restores the override folder byte for byte."""
    ours = GIVE_BAF.read_text(encoding="ascii").replace("%hg_splstate%", "195")
    if "%" in ours:
        return [f"give_ability.baf uses a variable this test does not fill in: {ours}"]
    bcs, out = compile_bafs(work, weidu, {"ours": ours, "old1": OTHER_BLOCK.format(n=1),
                                          "old2": OTHER_BLOCK.format(n=2)})
    if bcs is None:
        return [f"compiling the fixture scripts failed: {out[-1500:]}"]
    if not all(b.startswith(b"SC\n") and b.endswith(b"SC\n") for b in bcs.values()):
        return [f"unexpected BCS framing: {bcs['ours'][:8]!r}"]
    blocks = {n: b[3:-3] for n, b in bcs.items()}
    campaign = fg.make_2da(["WORLDSCRIPT", "SAVE_DIR", "WORLDSCRIPT"],
                           [("SOA", ["BALDUR", "save", "BALDUR"]), ("TUT", ["baldur", "save", "baldur"]),
                            ("TOB", ["BALDUR25", "save", "BALDUR25"]), ("SOD", ["BDBALDUR", "save", "BDBALDUR"])],
                           "*")
    fails = []
    for name, (table, want) in {"campaigns": (campaign, {"BALDUR", "BALDUR25"}),
                                "no_campaign_table": (None, {"BALDUR"})}.items():
        biff = {**script_ids(), "BALDUR25.BCS": bcs["old2"], **({"CAMPAIGN.2DA": table} if table else {})}
        g = fg.FakeGame(work / f"ew_{name}", weidu, EW_TP2, biff=biff,
                        override={"BALDUR.BCS": bcs["old1"], "AR0602.BCS": bcs["old1"]})
        (g.root / "cbprtest/give_ability.baf").write_bytes(GIVE_BAF.read_bytes())
        before = g.override()
        out = g.install()
        problems = []
        if not fg.installed_ok(out) or "ERROR" in out or g.results(out, "EW") != [str(len(want))]:
            problems.append(f"results {g.results(out, 'EW')}: {out[-800:]}")
        else:
            for script, old in (("BALDUR", "old1"), ("BALDUR25", "old2"), ("AR0602", "old1"), ("BDBALDUR", None)):
                path = find_ci(g.root / "override", f"{script}.bcs")
                got = path.read_bytes() if path else None
                if script in want:
                    exp = b"SC\n" + blocks["ours"] + blocks[old] + b"SC\n"
                else:
                    exp = bcs[old] if script in ("BALDUR", "AR0602") else None
                if got != exp:
                    problems.append(f"{script}.BCS: {'missing' if got is None else got[:60]!r}")
        g.uninstall()
        if g.override() != before:
            problems.append("uninstall did not restore the override folder")
        fails += [f"{name}: {p}" for p in problems]
    return fails


# --- CHARSND.2DA layout check ---------------------------------------------------------

def charsnd(labels, voices=("MALE", "FEMALE", "GROMVP")):
    rows = [(str(r), [str(5000 + i * 100 + int(r)) if str(r).isdigit() and int(r) < 35 and i == 2 else "-1"
                      for i in range(len(voices))]) for r in labels]
    return fg.make_2da(list(voices), rows)


CS_TP2 = r"""ACTION_FOR_EACH n IN CBPRHG GROMVP BEGIN
  COPY_EXISTING - ~charsnd.2da~ ~override~
    LPF hg_charsnd_check STR_VAR name = EVAL ~%n%~ RET ok present END
    PATCH_PRINT ~RESULT CS %n% %ok% %present%~
END
"""


@test
def charsnd_check(work, weidu):
    """Only a table with the 99 rows 1-99 in order is accepted; present names an existing column."""
    cases = {
        "rows_1_to_99": (list(range(1, 100)), ["CBPRHG 1 0", "GROMVP 1 1"]),
        "98_rows": (list(range(1, 99)), ["CBPRHG 0 0", "GROMVP 0 1"]),
        "gap_at_50": ([r for r in range(1, 101) if r != 50], ["CBPRHG 0 0", "GROMVP 0 1"]),
        "swapped_rows": ([2, 1] + list(range(3, 100)), ["CBPRHG 0 0", "GROMVP 0 1"]),
    }
    # With one or two columns WeiDU counts the "2DA V1.0" line among the rows as well.
    cases["one_column"] = (list(range(1, 100)), ["CBPRHG 1 0", "GROMVP 1 1"], ("GROMVP",))
    cases["two_columns"] = (list(range(1, 100)), ["CBPRHG 1 1", "GROMVP 1 0"], ("MALE", "CBPRHG"))
    fails = []
    for name, (labels, want, *voices) in cases.items():
        table = charsnd(labels, *voices)
        g = fg.FakeGame(work / f"cs_{name}", weidu, CS_TP2, biff={"CHARSND.2DA": table})
        out = g.install()
        got = g.results(out, "CS")
        if not fg.installed_ok(out) or got != want:
            fails.append(f"{name}: {got}, want {want}")
    return fails


# --- Subtitles of sound clips ----------------------------------------------------------

CV_TLK = [
    ("", ""),                                       # 0
    ("Original", ""),                               # 1
    ("[HOBGOBLIN 01] You be quiet!", "hobgl01"),    # 2 the lowest string with text (sound in lower case)
    ("You be quiet, too!", "HOBGL01"),              # 3 later: not used
    ("[HOBGOBLIN 06]", "HOBGL06"),                  # 4 only a tag, no text ...
    ("Rrr!", "HOBGL06"),                            # 5 ... so this later string's text is used
    ("  [X] Manure ~mouth~.  ", "HOBGL02"),         # 6 spaces, tag and tildes go
    ("Other text", "HOBGL02"),                      # 7 later: not used
    ("[HOBGOBLIN 08]", "HOBGL08"),                  # 8 no text at all
    ("Human line", "HUMAN01"),                      # 9 another clip
]
CV_ORIG = [(text, sound.upper()) for text, sound in CV_TLK]
CV_TEXTS = {"HOBGL01": "You be quiet!", "HOBGL02": "Manure mouth.", "HOBGL06": "Rrr!", "HOBGL08": ""}
TT_TP2 = r"""COPY - ~lang/en_us/dialog.tlk~ ~override~
  LPF hg_tlk_clip_texts STR_VAR clips = ~hobgl01 HOBGL02  HOBGL06 HOBGL08 HOBGL03~ RET_ARRAY t = texts END
  PHP_EACH t AS k => v BEGIN
    PATCH_PRINT ~RESULT TT %k%=<%v%>~
  END
COPY - ~cbprtest/setup-cbprtest.tp2~ ~override~
  LPF hg_tlk_clip_texts STR_VAR clips = ~HOBGL01~ RET_ARRAY u = texts END
  SET n = 0
  PHP_EACH u AS k => v BEGIN
    SET n += 1
  END
  PATCH_PRINT ~RESULT TT other-file %n%~
"""


@test
def tlk_clip_texts(work, weidu):
    """Each clip's subtitle is the text of the lowest string that plays it (sound names in
    any case) without a leading "[TAG]", "~" and outer spaces; a later string with text wins
    over earlier ones without; a clip no string plays gets none; a file that is no TLK
    gives nothing."""
    g = fg.FakeGame(work / "tt", weidu, TT_TP2, tlk=fg.make_tlk(CV_TLK))
    out = g.install()
    got = sorted(g.results(out, "TT"))
    want = sorted([f"{k}=<{v}>" for k, v in CV_TEXTS.items()] + ["other-file 0"])
    return [] if fg.installed_ok(out) and got == want else [f"{got}, want {want}"]


# --- Curated voice set from the game's sound clips (cd_add_soundset) -------------------

LINE = "filenames_stringrefs['CBPRHG'] = {4242, 2}"
OTHERS = ["filenames_stringrefs['GROMVP'] = {68790, 2}", "filenames_stringrefs['VICOB1'] = {329940, 2}"]
# Lines that mention the name but give it no menu name.
NEAR_MISSES = ["-- filenames_stringrefs['CBPRHG'] = {1, 2}", "filenames_stringrefs['CBPRHG2'] = {5, 2}",
               "filenames_stringrefs['XCBPRHG'] = {6, 2}", "local old = filenames_stringrefs['CBPRHG']"]
CRLF_LUA = ("    \r\n" + "\r\n".join(OTHERS) + "\r\n").encode()
CV_CLIPS = {"HOBGL01": b"OggS-one", "HOBGL02": b"OggS-two", "HOBGL03": b"OggS-three", "HOBGL06": b"OggS-six",
            "HOBGL08": b"OggS-eight"}  # no HOBGL05
# slot: (clip, file name suffix, CHARSND.2DA row in BG2:EE and EET, row in BG:EE), from the
# EE Soundset Tool's documentation; select_rare1 and action4 are rows the games order apart.
CV_SLOTS = {"common1": ("HOBGL01", "f", 26, 26), "select_rare1": ("hobgl02", "w_", 75, 35),
            "action1": ("HOBGL03", "i", 32, 32), "action4": ("HOBGL06", "s", 35, 79),
            "leader1": ("HOBGL03", "b", 6, 6), "damage1": ("HOBGL08", "l", 18, 18)}
CV_ARGS = " ".join(f"clip_{slot} = ~{clip}~" for slot, (clip, *_) in CV_SLOTS.items()) + " clip_gen_death1 = ~HOBGL05~"
CV_TP2 = r"""LAF hg_clip_voice INT_VAR display = RESOLVE_STR_REF (~Hobgoblin~)
  STR_VAR name = ~{NAME}~ tra = ~cbprtest/voice.tra~ {CLIPS}
  RET slots END
PRINT ~RESULT CV %slots%~
"""


def cv_game(work, weidu, case, game="bg2ee", name="CBPRHG", clips=CV_ARGS, table=None, where="biff", lua=None,
            sounds_folder=True, twice=False):
    body = CV_TP2.replace("{NAME}", name).replace("{CLIPS}", clips) * (2 if twice else 1)
    biff = {"HOBGL01.WAV": CV_CLIPS["HOBGL01"], "HOBGL02.WAV": CV_CLIPS["HOBGL02"]}
    override = {f"{c}.WAV": CV_CLIPS[c] for c in ("HOBGL03", "HOBGL06", "HOBGL08")}
    table = charsnd(range(1, 100)) if table is None else table
    if where == "biff":
        biff["CHARSND.2DA"] = table
    elif where == "override":
        override["CHARSND.2DA"] = table
    if lua is not None:
        override["M_cdsnd.lua"] = lua
    return fg.FakeGame(work / f"cv_{case}", weidu, body, tlk=fg.make_tlk(CV_TLK), biff=biff, override=override,
                       sounds_folder=sounds_folder, game=game)


@test
def clip_voice(work, weidu):
    """Each filled slot lands in the EE Soundset Tool's CHARSND.2DA row for the game
    (BG2:EE and EET order, BG:EE order); its line is the clip's game subtitle with a copy
    of the clip under the slot's file name (one-character suffixes into
    lang/<language>/sounds, also when that folder is missing, two-character ones into
    override); one clip can serve two slots; a clip the game lacks is warned about and its
    slot stays empty; the menu name joins the other voices' lines in M_cdsnd.lua (created
    when missing; lines that only look like ours do not count); every other column and
    string stays; a second call registers nothing; uninstall restores every game file and
    removes the scratch TRA."""
    cases = {
        "bg2ee": {},
        "eet": {"game": "eet"},
        "bgee": {"game": "bgee", "lua": CRLF_LUA},
        "override_table_lf_lua": {"where": "override", "lua": ("\n".join(OTHERS) + "\n").encode()},
        "lua_without_final_newline": {"lua": "\r\n".join(OTHERS).encode()},
        "lua_near_misses": {"lua": ("\r\n".join(OTHERS + NEAR_MISSES) + "\r\n").encode()},
        "no_sounds_folder": {"sounds_folder": False},
        "twice": {"twice": True},
    }
    fails = []
    for case, kw in cases.items():
        g = cv_game(work, weidu, case, **kw)
        before = g.tree()
        out = g.install()
        if not fg.installed_ok(out):
            fails.append(f"{case}: install failed: {out[-1500:]}")
            continue
        problems = [] if (g.root / "cbprtest/voice.tra").is_file() else ["no scratch TRA written"]
        want_results = ["6", "0"] if kw.get("twice") else ["6"]
        if g.results(out, "CV") != want_results:
            problems.append(f"slots {g.results(out, 'CV')}, want {want_results}")
        if "HOBGL05 (gen_death1)" not in out:
            problems.append("no warning about the missing clip")
        tlk = fg.tlk_entries(g.read("lang/en_us/dialog.tlk"))
        if tlk[:len(CV_ORIG)] != CV_ORIG:
            problems.append("existing strings changed")
        new = {e: i for i, e in enumerate(tlk) if i >= len(CV_ORIG)}
        bg1 = kw.get("game") == "bgee"
        want = {(row1 if bg1 else row2): new.get((CV_TEXTS.get(clip.upper(), ""), f"CBPRHG{suffix}".upper()))
                for clip, suffix, row2, row1 in CV_SLOTS.values()}
        table = g.root / "override/CHARSND.2DA"
        head, data = fg.table(table.read_bytes()) if table.is_file() else ([], {})
        ohead, odata = fg.table(charsnd(range(1, 100)))
        if head != ohead + ["CBPRHG"]:
            problems.append(f"header {head}")
        else:
            for r in range(1, 100):
                row, exp = data.get(str(r), []), want.get(r, -1)
                if exp is None or row[:-1] != odata[str(r)] or int(row[-1]) != exp:
                    problems.append(f"row {r}: {row}, want {exp}")
        files = {f"{'lang/en_us/sounds' if len(suffix) == 1 else 'override'}/cbprhg{suffix}.wav": CV_CLIPS[clip.upper()]
                 for clip, suffix, *_ in CV_SLOTS.values()}
        made = {p.relative_to(g.root).as_posix().lower(): p.read_bytes() for p in g.root.rglob("*")
                if p.is_file() and p.name.lower().startswith("cbprhg") and "backup" not in p.parts}
        if made != files:
            problems.append(f"sound files {sorted(made)}, want {sorted(files)}")
        lua = kw.get("lua")
        menu = g.root / "override/M_cdsnd.lua"
        lines = [ln.strip() for ln in menu.read_text(encoding="utf-8").splitlines() if ln.strip()] if menu.is_file() else []
        ours = [ln for ln in lines if ln.startswith("filenames_stringrefs['CBPRHG']")]
        old = [ln.strip() for ln in lua.decode().splitlines() if ln.strip()] if lua is not None else []
        try:
            named = len(ours) == 1 and tlk[int(ours[0].split("{")[1].split(",")[0])] == ("Hobgoblin", "")
        except (IndexError, ValueError):
            named = False
        if not named or lines != old + ours:
            problems.append(f"menu file {lines}")
        g.uninstall()
        after = g.tree()
        if after != before:
            problems.append(f"uninstall left {sorted(set(after.items()) ^ set(before.items()))}")
        if (g.root / "cbprtest/voice.tra").exists():
            problems.append("uninstall left the scratch TRA")
        if fg.tlk_entries(g.read("lang/en_us/dialog.tlk"))[:len(CV_ORIG)] != CV_ORIG:
            problems.append("uninstall changed existing strings")
        fails += [f"{case}: {p}" for p in problems]
    return fails


@test
def clip_voice_refused(work, weidu):
    """No voice set and no file changes when CHARSND.2DA is missing or lacks the 99
    numbered rows, when the name is taken (CHARSND.2DA column, M_cdsnd.lua menu name, a
    sound file the voice would write in either folder), when the game has none of the
    clips, or when no clip fills a one-character slot (the voice menu would not list the
    voice); a name longer than six characters stops the install."""
    taken = fg.make_2da(["MALE", "CBPRHG"], [(str(r), ["-1", "-1"]) for r in range(1, 100)])
    menu = "\r\n".join(["filenames_stringrefs['GROMVP'] = {68790, 2}",
                        '  filenames_stringrefs[ "CBPRHG" ] = {1, 2}', ""]).encode()
    fails = []
    for case, kw, outcome, extra in (
            ("98_row_table", {"table": charsnd(range(1, 99))}, "0", {}),
            ("no_table", {"where": None}, "0", {}),
            ("column_taken", {"table": taken}, "0", {}),
            ("menu_name_taken", {"lua": menu}, "0", {}),
            ("sound_file_taken", {}, "0", {"lang/en_us/sounds/CBPRHGf.wav": b"other"}),
            ("override_file_taken", {}, "0", {"override/CBPRHGw_.wav": b"other"}),
            ("no_clip_in_game", {"clips": "clip_common1 = ~HOBGL05~ clip_action1 = ~NOSUCH~"}, "0", {}),
            ("only_two_character_slots", {"clips": "clip_select_rare1 = ~HOBGL02~ clip_common5 = ~HOBGL01~"},
             "0", {}),
            ("name_too_long", {"name": "CBPRHOB"}, "fail", {})):
        g = cv_game(work, weidu, case, **kw)
        for rel, data in extra.items():
            (g.root / rel).write_bytes(data)
        before = g.tree()
        out = g.install()
        if outcome == "fail":
            ok = fg.failed(out)
        else:
            ok = fg.installed_ok(out) and g.results(out, "CV") == [outcome]
        if not ok or g.tree() != before:
            fails.append(f"{case}: results {g.results(out, 'CV')}, files changed: {g.tree() != before}")
    return fails


# --- Inventory figure from a creature BAM ----------------------------------------------

INV_TP2 = r"""LAF hg_make_inv_bam STR_VAR src = ~mhobg1~ dst = ~hgtinv~ END
"""


def creature_palette(green=0):
    """Palette (BGRA) whose only RGB(0,255,0) entry is `green` (None: no such entry)."""
    pal = [bytes([i, 255 - i, i // 2, 0]) for i in range(256)]  # entry 0 is the only green
    pal[0] = bytes([0, 0, 0, 0])
    if green is not None:
        pal[green] = bytes([0, 255, 0, 0])
    return b"".join(pal)


def creature_bam(cycles=17, rle=True, compressed=False, palette=None, rle_index=0, bg=0):
    """Creature BAM; `bg` is the figure's background (transparent) index."""
    palette = palette or creature_palette()
    fig = bytes(bg if v == 0 else v for v in (0, 0, 7, 0, 0,
                                              0, 9, 9, 9, 0,
                                              3, 0, 0, 0, 3,
                                              200, 201, 202, 203, 204))
    frames = [(3, 2, 1, 1, bytes([1, 2, 3, 4, 5, 6]), rle), (2, 2, 0, 0, bytes([0, 0, 0, 8]), rle),
              (5, 4, 2, 3, fig, rle)]
    cyc = [[0, 1]] * min(cycles, 16) + ([[2, 1]] if cycles > 16 else [])
    return fg.make_bam(frames, cyc, palette, rle_index=rle_index, compressed=compressed), palette, fig


@test
def inventory_figure(work, weidu):
    """Frame 0 of cycle 16 (through the lookup table), from a BIFF or override BAM, RLE or
    raw frame, BAM or BAMC, comes out 2x as a two-frame, one-cycle BAM with the palette;
    the blank frame's pixel is the transparent colour (first RGB(0,255,0) entry, else 0)
    and the header keeps the source's RLE index, also when these are not 0;
    a BAM without cycle 16 fails the install and writes nothing."""
    fails = []
    cases = {"biff_rle": ("biff", True, False, {}, 0), "override_bamc": ("override", True, True, {}, 0),
             "raw_frame": ("biff", False, False, {}, 0),
             "green_and_rle_index_5": ("biff", True, False,
                                       {"palette": creature_palette(5), "rle_index": 5, "bg": 5}, 5),
             "no_green_rle_index_7": ("override", True, False,
                                      {"palette": creature_palette(None), "rle_index": 7}, 0)}
    for name, (where, rle, compressed, kw, blank) in cases.items():
        bam, palette, fig = creature_bam(rle=rle, compressed=compressed, **kw)
        res = {"MHOBG1.BAM": bam}
        g = fg.FakeGame(work / f"inv_{name}", weidu, INV_TP2, biff=res if where == "biff" else None,
                        override=res if where == "override" else None)
        out = g.install()
        if not fg.installed_ok(out):
            fails.append(f"{name}: install failed: {out[-800:]}")
            continue
        data = g.read("override/hgtinv.bam")
        frames, cycles, lookup, pal = fg.read_bam(data)
        scaled = bytes(fig[(y // 2) * 5 + x // 2] for y in range(8) for x in range(10))
        if frames != [(10, 8, -4, -16, scaled), (1, 1, 0, 0, bytes([blank]))]:
            fails.append(f"{name}: frames {[f[:4] for f in frames]} blank {frames[1][4:] if len(frames) > 1 else ''}")
        if cycles != [(3, 0)] or lookup != [0, 0, 1] or pal != palette:
            fails.append(f"{name}: cycles {cycles} lookup {lookup} palette {'ok' if pal == palette else 'differs'}")
        if data[0x0B] != kw.get("rle_index", 0):
            fails.append(f"{name}: header RLE index {data[0x0B]}, want {kw.get('rle_index', 0)}")
    bam, _, _ = creature_bam(cycles=16)
    g = fg.FakeGame(work / "inv_no_cycle_16", weidu, INV_TP2, biff={"MHOBG1.BAM": bam})
    before = g.override()
    out = g.install()
    if not fg.failed(out) or g.override() != before:
        fails.append("no_cycle_16: the install did not fail cleanly")
    return fails


# --- The shipped sources ---------------------------------------------------------------

# cd_add_soundset.tph as the EE Soundset Tool ships it (Gibberlings3/EE_soundset_tool, also
# in every chriz-bg-voicepacks release).
SOUNDSET_TOOL_SHA256 = "a581fae61b165c0c8af8a6ad7136b7b1b825e14d379c528bfb89453a06f843c5"
# Slots the tool's authors found silent for player characters: common selection 7, the
# attack sounds (the weapon's sound plays instead) and the reputation reactions (NPCs only).
SILENT_FOR_PCS = {"common7", "attack1", "attack2", "attack3", "attack4", "happy", "unhappy_1", "unhappy_2",
                  "breaking_pt"}


@test
def soundset_tool_unchanged(work, weidu):
    """The EE Soundset Tool helper is shipped byte for byte as its authors publish it."""
    data = (MOD / "lib/cd_add_soundset.tph").read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return [] if digest == SOUNDSET_TOOL_SHA256 else [f"cd_add_soundset.tph has sha256 {digest}"]


@test
def hob_voice_curation(work, weidu):
    """The hobgoblin voice uses each of the game's ten hobgoblin clips (HOBGL01-HOBGL10), at
    most two of them for a second slot; selecting, ordering (moving) and attacking (battle
    cry) always have a line; no clip goes to a slot that is silent for player characters."""
    text = (MOD / "hobgoblin/hobgoblin.tpa").read_text(encoding="latin-1")
    call = text[text.index("LAF hg_clip_voice"):]
    call = call[:call.index("RET hg_voice_slots")]
    slots = re.findall(r"\bclip_(\w+)\s*=\s*~([^~]*)~", call)
    clips = [clip.upper() for _, clip in slots]
    fails = []
    if set(clips) != {f"HOBGL{i:02d}" for i in range(1, 11)}:
        fails.append(f"clips {sorted(set(clips))}")
    if len(clips) - len(set(clips)) > 2:
        fails.append(f"{len(clips) - len(set(clips))} clips serve a second slot")
    if len({slot for slot, _ in slots}) != len(slots):
        fails.append("a slot is named twice")
    for group in ("common", "action", "battlecry"):
        if not any(slot.startswith(group) for slot, _ in slots):
            fails.append(f"no {group} slot")
    if silent := sorted({slot for slot, _ in slots} & SILENT_FOR_PCS):
        fails.append(f"silent slots {silent}")
    return fails


@test
def sources_parse(work, weidu):
    """WeiDU parses the tp2, every tpa and the tph (also code the fake games above do not run);
    every language file loads, WeiDU reads the same strings from it as a plain reading, and
    it has every @N the tp2 and tpa files use."""
    sources = [("TP2", REPO / "setup-chriz-bg-playable-races.tp2")] + [("TPA", p) for p in sorted(MOD.rglob("*.tp[ah]"))]
    fails, used = [], set()
    for kind, path in sources:
        proc = subprocess.run([weidu, "--no-exit-pause", "--nogame", "--no-auto-tp2", "--parse-check", kind, str(path)],
                              cwd=work, stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        text = (proc.stdout + proc.stderr).decode("utf-8", "replace")
        if proc.returncode != 0 or "successfully parsed" not in text:
            fails.append(f"{path.relative_to(REPO).as_posix()}: {text[-400:]}")
        used |= {int(n) for n in re.findall(r"(?<![\w@])@(\d+)\b", path.read_text(encoding="latin-1"))}
    tras = sorted((MOD / "lang").rglob("*.tra"))
    if not tras:
        fails.append("no language files")
    for tra in tras:
        entries = {n: s for n, s in re.findall(r"@(\d+)\s*=\s*~([^~]*)~", tra.read_text(encoding="utf-8"))}
        if missing := sorted(used - {int(n) for n in entries}):
            fails.append(f"{tra.parent.name}/{tra.name} lacks {missing}")
        body = "LOAD_TRA ~cbprtest/lang.tra~\n" + "".join(f"OUTER_SPRINT t @{n}\nPRINT ~RESULT TRA {n} %t%~\n"
                                                          for n in entries)
        g = fg.FakeGame(work / f"tra_{tra.parent.name}", weidu, body)
        (g.root / "cbprtest/lang.tra").write_bytes(tra.read_bytes())
        out = g.install()
        got = dict((r.split(" ", 1) + [""])[:2] for r in g.results(out, "TRA"))
        if not fg.installed_ok(out) or got != entries:
            fails.append(f"{tra.parent.name}/{tra.name}: WeiDU reads {got}, plain reading {entries}")
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weidu", required=True, help="weidu.exe (or any mod's setup-*.exe), version 249 or newer")
    ap.add_argument("--keep", type=Path, help="keep the fake games in this folder")
    ap.add_argument("only", nargs="*", help="run only these tests")
    args = ap.parse_args()
    work = args.keep or Path(tempfile.mkdtemp(prefix="cbpr-tests-"))
    work.mkdir(parents=True, exist_ok=True)
    failures = 0
    try:
        for fn in TESTS:
            if args.only and fn.__name__ not in args.only:
                continue
            fails = fn(work, args.weidu)
            failures += bool(fails)
            print(f"{'PASS' if not fails else 'FAIL'} {fn.__name__}", flush=True)
            for f in fails:
                print(f"    {f}", flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    print("all tests passed" if not failures else f"{failures} test(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

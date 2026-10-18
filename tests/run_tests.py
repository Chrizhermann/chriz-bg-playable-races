"""Offline tests for the installer library: real WeiDU runs in small synthetic game folders,
no game installation or game files needed (all test data is made up in fakegame.py).

usage: python tests/run_tests.py --weidu <path to weidu.exe or a mod's setup-*.exe> [--keep DIR]
Exit code 0 when every test passes.
"""
import argparse
import hashlib
import math
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
        # Vanilla BG:EE and BG2:EE 2.7: the columns, no rows.
        "header_only": (["WORLDSCRIPT", "DESCRIPTION", "SAVE_DIR", "RACETEXT"], [], set()),
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


# --- Weapon groups and bodies ----------------------------------------------------------

MELEE_TYPES = "16 17 18 19 20 21 22 23 25 26 29 30 44 57 69"
WL_TP2 = r"""LAF hg_weapon_layout STR_VAR melee_types = ~%s~ ranged_types = ~15 27~ base_codes = ~S1 HB~
  RET nbodies nslots RET_ARRAY melee ranged groups bodies slot_body slot_letter slot_group END
ACTION_PHP_EACH melee AS key => code BEGIN
  OUTER_SPRINT g $groups(~%%key%%~)
  OUTER_SET b = $bodies(~%%key%%~)
  PRINT ~RESULT WL code %%code%% %%g%% %%b%%~
END
OUTER_FOR (i = 0; i < nslots; ++i) BEGIN
  OUTER_SET b = $slot_body(~%%i%%~)
  OUTER_SPRINT l $slot_letter(~%%i%%~)
  OUTER_SPRINT g $slot_group(~%%i%%~)
  PRINT ~RESULT WL slot %%b%% %%l%% %%g%%~
END
ACTION_PHP_EACH ranged AS key => code BEGIN
  PRINT ~RESULT WL ranged %%code%%~
END
PRINT ~RESULT WL bodies %%nbodies%%~
""" % MELEE_TYPES
# (item type, look code) of the fixture items; several items may share a code.
WL_ITEMS = [
    (20, b"S1"), (30, b"HB"), (25, b"AX"), (29, b"SP"), (18, b"SL"), (17, b"MC"), (22, b"MS"),
    (23, b"FL"),
    (23, b"F0"), (23, b"F0"), (20, b"F0"),   # unknown code: most of its items are flails
    (19, b"F2"),                             # unknown code of a short sword
    (23, b"FS"),                             # IESDP's flame sword stays a sword
    (26, b"Q2"), (29, b"Q2"),                # a tie: spear comes before staff
    (25, b"hb"),                             # lower case is another code than HB
    (16, b"H6"),                             # a helmet's code on a dagger
    (15, b"BW"), (27, b"CB"),                # launchers
    (2, b"2A"), (20, b"  "), (20, b"\0\0"), (20, b"S-"),   # no look code of a weapon
]


def wl_game(work, weidu, name, items, override_items=()):
    biff = {f"WL{i:04d}.ITM": fg.make_itm(t, c) for i, (t, c) in enumerate(items)}
    biff["NOTITEM.ITM"] = fg.make_itm(20, b"AX", sig=b"SPL V1  ")
    over = {f"WO{i:04d}.ITM": fg.make_itm(t, c) for i, (t, c) in enumerate(override_items)}
    over["SHORT.ITM"] = b"ITM V1  " + bytes(20)
    return fg.FakeGame(work / f"wl_{name}", weidu, WL_TP2, biff=biff, override=over)


@test
def weapon_layout(work, weidu):
    """IESDP codes keep their group, other codes take the group of most of their items (a
    tie to the earlier group), lower and upper case are different codes; per first letter
    the base codes' groups take body 0 and the other groups the next bodies in group order;
    each body and letter in use gets one layer; launchers are listed apart; items in
    override count; no look code, another type or no ITM counts nothing; without any item the
    base codes still have their layers."""
    want_codes = {"S1 sword 0", "SP spear 1", "SL sling 2", "HB halberd 0", "hb axe 1", "H6 dagger 2",
                  "AX axe 0", "MC mace 0", "MS morningstar 1", "FL flail 1", "F0 flail 1", "F2 sword 0",
                  "FS sword 0", "Q2 spear 0", "WH hammer 0"}
    want_slots = {"0 S sword", "1 S spear", "2 S sling", "0 H halberd", "1 H axe", "2 H dagger", "0 A axe",
                  "0 M mace", "1 M morningstar", "0 F sword", "1 F flail", "0 Q spear", "0 W hammer"}
    cases = {
        "items": (WL_ITEMS, [(21, b"WH")], want_codes, want_slots, {"BW", "CB"}, "3"),
        "no_items": ([], [], set(), {"0 S sword", "0 H halberd"}, set(), "1"),
    }
    fails = []
    for name, (items, over, codes, slots, ranged, bodies) in cases.items():
        g = wl_game(work, weidu, name, items, over)
        out = g.install()
        got = g.results(out, "WL")
        got_codes = {r[5:] for r in got if r.startswith("code ")}
        got_slots = {r[5:] for r in got if r.startswith("slot ")}
        got_ranged = {r[7:] for r in got if r.startswith("ranged ")}
        got_bodies = [r[7:] for r in got if r.startswith("bodies ")]
        if not fg.installed_ok(out):
            fails.append(f"{name}: install failed: {out[-800:]}")
            continue
        if got_codes != codes:
            fails.append(f"{name}: codes {sorted(got_codes ^ codes)} differ")
        if got_slots != slots or len([r for r in got if r.startswith("slot ")]) != len(slots):
            fails.append(f"{name}: slots {sorted(got_slots)}, want {sorted(slots)}")
        if got_ranged != ranged:
            fails.append(f"{name}: ranged {sorted(got_ranged)}")
        if got_bodies != [bodies]:
            fails.append(f"{name}: bodies {got_bodies}, want {bodies}")
    return fails


# --- Frame geometry sums ---------------------------------------------------------------

sys.path.insert(0, str(REPO / "tools"))
import hob_weapon_art as art  # noqa: E402

GS_TP2 = r"""ACTION_FOR_EACH b IN geoa geob geoc geod BEGIN
  COPY_EXISTING - ~%b%.bam~ ~override~
    LPF hg_bam_decompress END
    LPF hg_bam_geometry_sum RET s1 = sum1 s2 = sum2 END
    PATCH_PRINT ~RESULT GS %b% %s1% %s2%~
END
"""


def geo_bams():
    """Four BAMs: b is a with other pixels, another frame order and compression, c moves one
    frame's centre by a pixel, d has a lookup entry that names no frame."""
    pal = creature_palette()
    f1, f2, f3 = (3, 2, 1, 1, bytes([1, 2, 3, 4, 5, 6])), (2, 2, -1, 0, bytes([0, 0, 0, 8])), \
        (4, 1, 2, -3, bytes([9, 9, 0, 9]))
    a = fg.make_bam([(*f1, True), (*f2, False), (*f3, True)], [[0, 1, 2], [2], [1, 1]], pal)
    other = lambda f: (*f[:4], bytes((v + 3) % 256 for v in f[4]))  # noqa: E731
    b = fg.make_bam([(*other(f3), False), (*other(f1), True), (*other(f2), True)], [[1, 2, 0], [0], [2, 2]], pal,
                    compressed=True)
    c = fg.make_bam([(*f1, True), (f2[0], f2[1], 0, f2[3], f2[4], False), (*f3, True)], [[0, 1, 2], [2], [1, 1]], pal)
    d = fg.make_bam([(*f1, True), (*f2, False), (*f3, True)], [[0, 1, 2], [2], [1, 65535]], pal)
    return {"GEOA.BAM": a, "GEOB.BAM": b, "GEOC.BAM": c, "GEOD.BAM": d}


@test
def geometry_sum(work, weidu):
    """WeiDU's sums equal the art tool's for BAM and BAMC, RLE and raw frames; pixels, frame
    order and compression do not change them, a frame centre one pixel off and a lookup entry
    that names no frame do."""
    bams = geo_bams()
    g = fg.FakeGame(work / "gs", weidu, GS_TP2, biff={k: v for k, v in bams.items() if k != "GEOD.BAM"},
                    override={"GEOD.BAM": bams["GEOD.BAM"]})
    out = g.install()
    got = {r.split()[0].upper(): tuple(int(v) for v in r.split()[1:]) for r in g.results(out, "GS")}
    want = {k[:-4]: art.geometry_sums(v) for k, v in bams.items()}
    fails = [] if fg.installed_ok(out) and got == want else [f"WeiDU {got}, tool {want}"]
    if want["GEOA"] != want["GEOB"]:
        fails.append("pixels, frame order or compression changed the sums")
    if len({want["GEOA"], want["GEOC"], want["GEOD"]}) != 3:
        fails.append("a moved centre or a missing frame left the sums unchanged")
    return fails


GM_TP2 = r"""LAF hg_bam_geometry_matches INT_VAR sum1 = %d sum2 = %d STR_VAR name = ~geob~ RET ok END
PRINT ~RESULT GM right %%ok%%~
LAF hg_bam_geometry_matches INT_VAR sum1 = %d sum2 = %d STR_VAR name = ~geob~ RET ok END
PRINT ~RESULT GM wrong %%ok%%~
LAF hg_bam_geometry_matches INT_VAR sum1 = %d sum2 = %d STR_VAR name = ~nosuch~ RET ok END
PRINT ~RESULT GM missing %%ok%%~
"""


@test
def geometry_matches(work, weidu):
    """A BAM matches its own sums, not one sum off, and a missing BAM matches nothing."""
    bams = geo_bams()
    s1, s2 = art.geometry_sums(bams["GEOB.BAM"])
    g = fg.FakeGame(work / "gm", weidu, GM_TP2 % (s1, s2, s1, s2 + 1, s1, s2), biff={"GEOB.BAM": bams["GEOB.BAM"]})
    out = g.install()
    got = g.results(out, "GM")
    want = ["right 1", "wrong 0", "missing 0"]
    return [] if fg.installed_ok(out) and got == want else [f"{got}, want {want}"]


# --- Weapon art with the game's palette ------------------------------------------------

WA_TP2 = r"""LAF hg_copy_weapon_art INT_VAR remap_2h = 1 STR_VAR art = ~cbprtest/art.bam~ palette = ~mhobsg2~ dst = ~hgtsg2~ END
LAF hg_copy_weapon_art STR_VAR art = ~cbprtest/art.bam~ palette = ~mhobsg2~ dst = ~hgtsg1~ END
"""
WA_BAD_TP2 = r"""LAF hg_copy_weapon_art STR_VAR art = ~cbprtest/short.bam~ palette = ~mhobsg2~ dst = ~hgtbad~ END
"""


def art_bams():
    """The game's sword layer (24 cycles, a palette of its own) and an art BAMC with the
    same cycles, other frames and no palette, as the art tool writes it."""
    pal = creature_palette(0)
    game = fg.make_bam([(2, 2, 0, 0, bytes([1, 2, 3, 4]), True)], [[0]] * 24, pal, compressed=True)
    frames = [(1, 1, 0, 0, bytes([60 + i]), False) for i in range(24)]
    art_bam = fg.make_bam(frames, [[i] for i in range(24)], bytes(1024), compressed=True)
    short = fg.make_bam(frames[:20], [[i] for i in range(20)], bytes(1024), compressed=True)
    return game, pal, art_bam, short, frames


@test
def weapon_art_copy(work, weidu):
    """The art keeps its frames and cycles, takes the game BAM's palette and comes out as a
    plain BAM; with the two-handed remap cycles 16-23 show cycles 0-7; art with another cycle
    count than the game BAM stops the install and writes nothing."""
    game, pal, art_bam, short, frames = art_bams()
    g = fg.FakeGame(work / "wa", weidu, WA_TP2, biff={"MHOBSG2.BAM": game})
    (g.root / "cbprtest/art.bam").write_bytes(art_bam)
    out = g.install()
    if not fg.installed_ok(out):
        return [f"install failed: {out[-800:]}"]
    fails = []
    want_frames = [f[:5] for f in frames]
    for name, remap in (("hgtsg2", True), ("hgtsg1", False)):
        got_frames, cycles, lookup, got_pal = fg.read_bam(g.read(f"override/{name}.bam"))
        firsts = [lookup[first] for _, first in cycles]
        want = [i - 16 if remap and 16 <= i < 24 else i for i in range(24)]
        if got_frames != want_frames or got_pal != pal or firsts != want:
            fails.append(f"{name}: frames {'ok' if got_frames == want_frames else 'differ'}, palette "
                         f"{'ok' if got_pal == pal else 'differs'}, cycle frames {firsts}")
    bad = fg.FakeGame(work / "wa_bad", weidu, WA_BAD_TP2, biff={"MHOBSG2.BAM": game})
    (bad.root / "cbprtest/short.bam").write_bytes(short)
    before = bad.override()
    out = bad.install()
    if not fg.failed(out) or bad.override() != before:
        fails.append("art with 20 cycles: the install did not fail cleanly")
    return fails


# --- Weapon art drawing -----------------------------------------------------------------

def pieces(pixels):
    """How many 8-connected pieces a set of pixels makes."""
    left, n = set(pixels), 0
    while left:
        n += 1
        todo = [left.pop()]
        while todo:
            x, y = todo.pop()
            for q in [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]:
                if q in left:
                    left.remove(q)
                    todo.append(q)
    return n


def sword_geometry(angle, reach):
    """What the art tool measures in a sword frame, for a sword along `angle` that reaches
    `reach` pixels past the grip."""
    u = (math.cos(angle), math.sin(angle))
    at = lambda t: (u[0] * t, u[1] * t)  # noqa: E731
    return {"pommel": at(0), "grip": at(4), "base": at(8), "tip": at(4 + reach), "u": u, "n": (-u[1], u[0]),
            "width": 2, "count": 30}


@test
def art_shafts_whole(work, weidu):
    """A shaft has no gaps at any length or angle, from end to end (lab run 15 showed staves,
    spears and halberds as dotted lines: the tool set a fixed 41 points along any shaft), a
    shaft of 12 pixels or more has a dark edge that keeps to it, and each weapon made of
    connected parts comes out in one piece. Morning stars and flails are left out: their
    spikes and chain links stand apart."""
    fails = []
    o = (0.3, -0.2)
    for length in (8, 20, 40, 41, 64, 100, 140):
        for k in range(24):
            g = sword_geometry(k * math.pi / 12, 45.0)
            c = art.Canvas()
            t0, t1 = -0.4 * length, 0.6 * length
            art.shaft(c, g, o, t0, t1, art.WOOD, art.WOOD_DARK, 1)
            wood = {p for p, v in c.px.items() if v == art.WOOD}
            dark = {p for p, v in c.px.items() if v == art.WOOD_DARK}
            ends = {tuple(int(round(v)) for v in art.frm(o, g, t, 0)) for t in (t0, t1)}
            where = f"shaft of {length} px at {k * 15} degrees"
            if pieces(wood) != 1 or not ends <= wood:
                fails.append(f"{where}: {pieces(wood)} piece(s), ends {'in' if ends <= wood else 'missing'}")
            if length >= 12 and not dark:
                fails.append(f"{where}: no dark edge")
            if any(pieces(wood | {p}) != 1 for p in dark):
                fails.append(f"{where}: dark edge away from the shaft")
    for group in ("axe", "halberd", "spear", "staff", "mace", "hammer", "club", "dagger", "sling"):
        for k in range(24):
            for reach in (20.0, 45.0, 70.0):
                n = pieces(art.draw(group, sword_geometry(k * math.pi / 12, reach), frozenset()).px)
                if n != 1:
                    fails.append(f"{group} at {k * 15} degrees, reach {reach:.0f}: {n} pieces")
    return fails[:12] + ([f"... {len(fails) - 12} more"] if len(fails) > 12 else [])


PF_TP2 =r"""ACTION_FOR_EACH p IN HGP1 HGP2 HGP3 HGP4 BEGIN
  LAF hg_bam_prefix_free STR_VAR prefix = EVAL ~%p%~ RET free END
  PRINT ~RESULT PF %p% %free%~
END
"""


@test
def bam_prefix_free(work, weidu):
    """A prefix is taken by any BAM whose name starts with it, in the key or in override, in
    any case; other resource types with that start do not take it."""
    bam, _, _ = creature_bam()
    g = fg.FakeGame(work / "pf", weidu, PF_TP2, biff={"HGP1XYZ.BAM": bam, "HGP2G1.ITM": fg.make_itm(20, b"S1")},
                    override={"hgp3g1.bam": bam, "HGP4.CRE": fg.make_cre(0x8100, {})})
    out = g.install()
    got = g.results(out, "PF")
    want = ["HGP1 0", "HGP2 1", "HGP3 0", "HGP4 1"]
    return [] if fg.installed_ok(out) and got == want else [f"{got}, want {want}"]


# --- The hobgoblin row in the campaign race tables -------------------------------------

RACE_COLS = ["ID", "NAME", "DESCSTR", "UPPERCASE", "BIOGRAPHY"]
STD_RACES = [("HUMAN", ["1", "10", "20", "30", "40"]), ("ELF", ["2", "11", "21", "31", "41"]),
             ("HALF_ORC", ["7", "16", "26", "36", "46"])]
RR_TP2 = r"""COPY_EXISTING ~racetext.2da~ ~override~
  LPF hg_race_row INT_VAR id = 111 name_ref = 900 desc_ref = %s upper_ref = 902 bio_ref = 903
    STR_VAR label = ~HOBGOBLIN~ RET added END
  PATCH_PRINT ~RESULT RR %%added%%~
BUT_ONLY
"""


@test
def race_row(work, weidu):
    """The row goes in front of the first row without a description (also on top, behind
    the last row when all have one), its strings in the columns named for them wherever they
    are, the default value in any other column; without a description it is placed the same;
    a row with that label or that race already leaves the table as it was."""
    undescribed = [("TIEFLING", ["153", "17", "-1", "37", "47"]), ("VAMPIRE", ["125", "18", "-1", "38", "-1"])]
    hob = ["111", "900", "901", "902", "903"]
    cases = {
        "bg1_order": (RACE_COLS, STD_RACES + undescribed, "901", STD_RACES + [("HOBGOBLIN", hob)] + undescribed),
        "all_described": (RACE_COLS, STD_RACES, "901", STD_RACES + [("HOBGOBLIN", hob)]),
        "undescribed_on_top": (RACE_COLS, undescribed + STD_RACES, "901",
                               [("HOBGOBLIN", hob)] + undescribed + STD_RACES),
        "not_offered": (RACE_COLS, STD_RACES + undescribed, "0 - 1",
                        STD_RACES + [("HOBGOBLIN", ["111", "900", "-1", "902", "903"])] + undescribed),
        "other_columns": (["NAME", "ID", "EXTRA", "DESCSTR", "BIOGRAPHY", "UPPERCASE"],
                          [("HUMAN", ["10", "1", "5", "20", "40", "30"]), ("TIEFLING", ["17", "153", "5", "-1", "47", "37"])],
                          "901", [("HUMAN", ["10", "1", "5", "20", "40", "30"]),
                                  ("HOBGOBLIN", ["900", "111", "*", "901", "903", "902"]),
                                  ("TIEFLING", ["17", "153", "5", "-1", "47", "37"])]),
        "label_taken": (RACE_COLS, STD_RACES + [("HOBGOBLIN", ["161", "5", "6", "7", "8"])], "901", None),
        "race_taken": (RACE_COLS, STD_RACES + [("HOB_PC", ["111", "5", "-1", "7", "8"])], "901", None),
    }
    fails = []
    for name, (cols, rows, desc, want) in cases.items():
        table = fg.make_2da(cols, rows, "*" if name == "other_columns" else "-1")
        g = fg.FakeGame(work / f"rr_{name}", weidu, RR_TP2 % desc, biff={"RACETEXT.2DA": table})
        out = g.install()
        got = g.results(out, "RR")
        path = find_ci(g.root / "override", "racetext.2da")
        if not fg.installed_ok(out) or got != ["0" if want is None else "1"]:
            fails.append(f"{name}: results {got}: {out[-600:]}")
        elif want is None:
            if path is not None:
                fails.append(f"{name}: the table was written")
        else:
            data = path.read_bytes().decode("latin-1").splitlines()
            head, _ = fg.table(path.read_bytes())
            body = [(r.split()[0], r.split()[1:]) for r in data[3:] if r.split()]
            if head != cols or body != want:
                fails.append(f"{name}: {head} {body}")
    return fails


# --- The race choice in UI.MENU --------------------------------------------------------

MENU_RACE = """menu
{
	name 'CHARGEN_RACE'
	list
	{
		action "
			if chargen.races[currentChargenRace] then
				createCharScreen:OnRaceSelectButtonClick(chargen.races[currentChargenRace].id)
			end
			"
		table "chargen.races"
	}
}
""".replace("\n", "\r\n")
MENU_OTHER = "menu\r\n{\r\n\tname 'START'\r\n}\r\n"
RS_CALL = "createCharScreen:OnRaceSelectButtonClick("
RS_DRY_TP2 = r"""LAF hg_route_race_select INT_VAR race = 111 template = 7 dry_run = 1 RET routed END
PRINT ~RESULT RS %routed%~
"""
RS_TP2 = r"""LAF hg_route_race_select INT_VAR race = 111 template = 7 STR_VAR bio_map = ~[231709] = 900, [265365] = 900, ~
  RET routed END
PRINT ~RESULT RS %routed%~
LAF hg_route_race_select INT_VAR race = 111 template = 7 STR_VAR bio_map = ~[1] = 2, ~ RET routed END
PRINT ~RESULT RS %routed%~
"""
RS_PIECES = ("if id == 111 then", "id = 7", "pcall(cbprRaceBio)", "local chosen = 2", "chosen = 1",
             'pcall(function() C:SetGlobal("CBPR_HOBGOBLIN_CHARGEN", "GLOBAL", chosen) end)',
             "createCharScreen.OnRaceSelectButtonClick(createCharScreen, id)", "function cbprRaceBio()",
             'if type(bioRaceData) ~= "table" then return end', "if e[1] == 111 then return end",
             "if e[1] == 7 then base = e end", "local bio = {[231709] = 900, [265365] = 900, }",
             "local e = {111}", "for i = 2, #base do e[i] = bio[base[i]] or base[i] end",
             "table.insert(bioRaceData, e)")


def routed_block(menu, text):
    """The block appended to UI.MENU `menu` in `text`, line ends as LF, or None when the
    text is not `menu` with every race selection call routed plus one block."""
    routed = menu.replace(RS_CALL, "cbprRaceSelect(")
    block = text[len(routed):].replace("\r\n", "\n")
    # WeiDU writes the block with its own line ends (LF); UI.MENU keeps its own.
    if not text.startswith(routed) or not block.startswith("\n`\n-- Chriz BG Playable Races") \
            or not block.endswith("\nend\n`\n") or block.count("`") != 2 \
            or text.count("function cbprRaceSelect(") != 1 or RS_CALL in text:
        return None
    return block


@test
def route_race_select(work, weidu):
    """Every race selection call in UI.MENU (from a BIFF or override) goes through
    cbprRaceSelect, added once to the end, which turns race 111 into race 7 and sets the
    chargen global (1 for 111, 2 for any other race) without calling itself, and gives race 111
    race 7's bioRaceData entry with the mapped biographies; a second call finds it routed and
    adds nothing; a dry run tells the same and changes nothing; a UI.MENU without the call,
    or none at all, stays as it is; uninstall restores UI.MENU."""
    fails = []
    for name, (where, menu, want) in {"biff": ("biff", MENU_RACE + MENU_OTHER, "1"),
                                      "override": ("override", MENU_OTHER + MENU_RACE + MENU_RACE, "1"),
                                      "other_ui": ("override", MENU_OTHER, "0"),
                                      "no_menu": (None, None, "0")}.items():
        res = {"UI.MENU": menu.encode("ascii")} if menu else {}
        for dry in (True, False):
            g = fg.FakeGame(work / f"rs_{name}{'_dry' if dry else ''}", weidu, RS_DRY_TP2 if dry else RS_TP2,
                            biff=res if where == "biff" else None, override=res if where == "override" else None)
            before = g.tree()
            out = g.install()
            got = g.results(out, "RS")
            if not fg.installed_ok(out) or got != [want] * (1 if dry else 2):
                fails.append(f"{name}{' dry' if dry else ''}: results {got}: {out[-600:]}")
                continue
            if dry or want == "0":
                if g.tree() != before:
                    fails.append(f"{name}{' dry' if dry else ''}: files changed")
                continue
            text = find_ci(g.root / "override", "ui.menu").read_bytes().decode("ascii")
            block = routed_block(menu, text)
            if block is None:
                fails.append(f"{name}: UI.MENU {text[-900:]!r}")
                continue
            fails += [f"{name}: the block lacks {p!r}" for p in RS_PIECES if p not in block]
            if "[1] = 2" in block:
                fails.append(f"{name}: the second call changed the block")
            g.uninstall()
            if g.tree() != before:
                fails.append(f"{name}: uninstall did not restore the files")
    return fails


# --- 2DA rows: lookup and copy ------------------------------------------------------------

LK_TP2 = r"""COPY_EXISTING - ~racetext.2da~ ~override~
  LPF hg_2da_lookup STR_VAR key_col = ~ID~ key = ~7~ value_col = ~BIOGRAPHY~ RET found value END
  PATCH_PRINT ~RESULT LK %found% [%value%]~
  LPF hg_2da_lookup STR_VAR key_col = ~id~ key = ~99~ value_col = ~BIOGRAPHY~ RET found value END
  PATCH_PRINT ~RESULT LK %found% [%value%]~
  LPF hg_2da_lookup STR_VAR key_col = ~ID~ key = ~7~ value_col = ~NOPE~ RET found value END
  PATCH_PRINT ~RESULT LK %found% [%value%]~
  LPF hg_2da_lookup STR_VAR key_col = ~NAME~ key = ~abc~ value_col = ~descstr~ RET found value END
  PATCH_PRINT ~RESULT LK %found% [%value%]~
"""


@test
def lookup_2da(work, weidu):
    """The first row whose key column holds the key gives the value; column names and the key
    match in any letter case; no matching row or a missing column gives nothing."""
    table = fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HALF_ORC", ["7", "16", "26", "36", "46"]),
                                    ("OTHER_ORC", ["7", "ABC", "27", "37", "47"])])
    g = fg.FakeGame(work / "lk", weidu, LK_TP2, biff={"RACETEXT.2DA": table})
    out = g.install()
    got = g.results(out, "LK")
    want = ["1 [46]", "0 []", "0 []", "1 [27]"]
    return [] if fg.installed_ok(out) and got == want else [f"{got}, want {want}: {out[-600:]}"]


SB_TP2 = r"""LAF hg_race_skill_bonuses INT_VAR race = %d RET found RET_ARRAY bonuses END
OUTER_SPRINT list ~~
ACTION_PHP_EACH bonuses AS op => v BEGIN OUTER_SPRINT list ~%%list%% %%op%%=%%v%%~ END
PRINT ~RESULT SB %%found%%%%list%%~
"""
SKILL_COLS = ["PICK_POCKETS", "OPEN_LOCKS", "FIND_TRAPS", "MOVE_SILENTLY", "HIDE_IN_SHADOWS", "DETECT_ILLUSION",
              "SET_TRAPS"]
SKILL_OPS = [92, 90, 91, 59, 275, 276, 277]
SKILL_ROWS = [("HUMAN", ["15", "10", "5", "10", "5", "10", "0"]), ("HALF_ELF", ["25", "10", "5", "10", "10", "15", "0"]),
              ("HALFORC", ["15", "10", "10", "10", "5", "5", "0"]), ("GNOME", ["15", "15", "15", "15", "10", "20", "5"])]


def skill_bonuses(values):
    return {op: int(v) for op, v in zip(SKILL_OPS, values) if int(v) != 0}


@test
def race_skill_bonuses(work, weidu):
    """A player race's SKILLRAC row as the engine reads it: under the engine's own row names
    (HALF_ELF, HALFORC), the label in any letter case, the skill columns in any order and
    among others; values below 0 count, 0 does not. A missing row or column reads as the
    table's default value. No table, or a race outside the seven, gives nothing, even with a
    row of that race's name (the engine never reads it)."""
    orc = ["15", "10", "10", "10", "5", "5", "0"]
    order = [3, 0, 6, 2, 5, 1, 4]
    shuffled = ["EXTRA"] + [SKILL_COLS[i] for i in order]
    cases = {  # name: (race, table or None, found, bonuses)
        "halforc": (7, fg.make_2da(SKILL_COLS, SKILL_ROWS, "0"), 1, skill_bonuses(orc)),
        "human": (1, fg.make_2da(SKILL_COLS, SKILL_ROWS, "0"), 1, skill_bonuses(SKILL_ROWS[0][1])),
        "half_elf": (3, fg.make_2da(SKILL_COLS, SKILL_ROWS, "0"), 1, skill_bonuses(SKILL_ROWS[1][1])),
        "other_order": (7, fg.make_2da(shuffled, [(n, ["99"] + [v[i] for i in order]) for n, v in SKILL_ROWS], "0"), 1,
                        skill_bonuses(orc)),
        "lower_case": (7, fg.make_2da(SKILL_COLS, [("halforc", orc)], "0"), 1, skill_bonuses(orc)),
        "negative": (7, fg.make_2da(SKILL_COLS, [("HALFORC", ["15", "10", "10", "-5", "5", "5", "0"])], "0"), 1,
                     {92: 15, 90: 10, 91: 10, 59: -5, 275: 5, 276: 5}),
        "no_row": (7, fg.make_2da(SKILL_COLS, SKILL_ROWS[:2], "0"), 0, {}),
        "no_row_default": (7, fg.make_2da(SKILL_COLS, SKILL_ROWS[:2], "3"), 0, {op: 3 for op in SKILL_OPS}),
        "no_column": (7, fg.make_2da(SKILL_COLS[:6], [(n, v[:6]) for n, v in SKILL_ROWS], "4"), 1,
                      {**skill_bonuses(orc), 277: 4}),
        "no_table": (7, None, 0, {}),
        "race_111": (111, fg.make_2da(SKILL_COLS, SKILL_ROWS + [("HOBGOBLIN", orc)], "0"), 0, {}),
    }
    fails = []
    for name, (race, table, found, want) in cases.items():
        biff = {"SKILLRAC.2DA": table} if table is not None else {}
        g = fg.FakeGame(work / f"sb_{name}", weidu, SB_TP2 % race, biff=biff)
        out = g.install()
        got = g.results(out, "SB")
        if not fg.installed_ok(out) or len(got) != 1:
            fails.append(f"{name}: {got}: {out[-600:]}")
            continue
        words = got[0].split()
        bonuses = {int(w.split("=")[0]): int(w.split("=")[1]) for w in words[1:]}
        if words[0] != str(found) or bonuses != want:
            fails.append(f"{name}: found {words[0]}, bonuses {bonuses}; want {found}, {want}")
    return fails


# --- The race in character creation ---------------------------------------------------------

OF_TP2 = r"""LAF hg_offer_race INT_VAR race = 111 template = 7 name_ref = 900 desc_ref = 901 upper_ref = 902
  bio_ref = 903 STR_VAR label = ~HOBGOBLIN~ RET tables routed END
PRINT ~RESULT OF %tables% %routed%~
"""
OF_CAMPAIGN = fg.make_2da(["WORLDSCRIPT", "SAVE_DIR", "RACETEXT"],
                          [("SOA", ["BALDUR", "save", "RACETEXT"]), ("TOB", ["BALDUR25", "save", "RACETEXT"]),
                           ("BG1", ["BALDUR", "save", "BGRACTXT"]), ("SOD", ["BDBALDUR", "save", "SODRACE"]),
                           ("BP1", ["BALDUR", "bpsave", "*"]), ("TUT", ["BALDUR", "save", "bgractxt"])], "*")
# Vanilla BG:EE and BG2:EE 2.7: the columns, no rows.
OF_CAMPAIGN_EMPTY = fg.make_2da(["WORLDSCRIPT", "SAVE_DIR", "CLASTEXT", "RACETEXT"], [], "*")


def of_table(bio):
    """A race table: human, half-orc (biography `bio`), tiefling (not offered)."""
    return fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HALF_ORC", ["7", "16", "26", "36", bio]),
                                   ("TIEFLING", ["153", "17", "-1", "37", "-1"])])


@test
def offer_race(work, weidu):
    """The row goes into each race table the campaigns name (any letter case, once each) and
    RACETEXT.2DA, if the game has them; its description only where UI.MENU can route the choice,
    its biography only where the template race has one; the routed choice maps each of the
    template's biographies to the race's own; with every table holding the race already, nothing
    changes; uninstall restores the files."""
    eet = {"CAMPAIGN.2DA": OF_CAMPAIGN, "RACETEXT.2DA": of_table("-1"), "BGRACTXT.2DA": of_table("231709"),
           "SODRACE.2DA": of_table("265365")}
    taken = {t: fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HOB", ["111", "5", "6", "7", "8"])])
             for t in ("RACETEXT.2DA", "BGRACTXT.2DA", "SODRACE.2DA")}
    menu = (MENU_RACE + MENU_OTHER).encode("ascii")
    cases = {  # name: (resources, rows {table: (desc, bio)}, routed, biographies mapped)
        "eet": ({**eet, "UI.MENU": menu}, {"RACETEXT": ("901", "-1"), "BGRACTXT": ("901", "903"),
                                           "SODRACE": ("901", "903")}, "1", {"231709", "265365"}),
        "vanilla": ({"CAMPAIGN.2DA": OF_CAMPAIGN_EMPTY, "RACETEXT.2DA": of_table("555"), "UI.MENU": menu},
                    {"RACETEXT": ("901", "903")}, "1", {"555"}),
        "no_campaign": ({"RACETEXT.2DA": of_table("-1"), "UI.MENU": menu}, {"RACETEXT": ("901", "-1")}, "1", set()),
        "missing_table": ({k: v for k, v in eet.items() if k != "SODRACE.2DA"} | {"UI.MENU": menu},
                          {"RACETEXT": ("901", "-1"), "BGRACTXT": ("901", "903")}, "1", {"231709"}),
        "no_route": ({**eet, "UI.MENU": MENU_OTHER.encode("ascii")},
                     {"RACETEXT": ("-1", "-1"), "BGRACTXT": ("-1", "903"), "SODRACE": ("-1", "903")}, "0", None),
        "taken": ({"CAMPAIGN.2DA": OF_CAMPAIGN, **taken, "UI.MENU": menu}, {}, "0", None),
    }
    fails = []
    for name, (res, rows, routed, bios) in cases.items():
        g = fg.FakeGame(work / f"of_{name}", weidu, OF_TP2, biff=res)
        before = g.tree()
        out = g.install()
        got = g.results(out, "OF")
        if not fg.installed_ok(out) or got != [f"{len(rows)} {routed}"]:
            fails.append(f"{name}: results {got}: {out[-800:]}")
            continue
        for t in ("RACETEXT", "BGRACTXT", "SODRACE"):
            path = find_ci(g.root / "override", f"{t}.2da")
            if t not in rows:
                if path is not None:
                    fails.append(f"{name}: {t}.2DA was written")
                continue
            _, body = fg.table(path.read_bytes()) if path else (None, {})
            desc, bio = rows[t]
            if body.get("HOBGOBLIN") != ["111", "900", desc, "902", bio]:
                fails.append(f"{name}: {t} row {body.get('HOBGOBLIN')}")
        ui = find_ci(g.root / "override", "ui.menu")
        if routed == "1":
            block = routed_block(menu.decode("ascii"), ui.read_bytes().decode("ascii")) if ui else None
            mapped = None
            if block and "local bio = {" in block:
                fields = block.split("local bio = {", 1)[1].split("}", 1)[0]
                mapped = {f.split("]")[0].strip("[ ") for f in fields.split(",") if f.strip()}
                if any(f.split("=")[1].strip() != "903" for f in fields.split(",") if f.strip()):
                    mapped = None
            if mapped != bios:
                fails.append(f"{name}: biographies mapped {mapped}, want {bios}")
        elif ui is not None:
            fails.append(f"{name}: UI.MENU was written")
        g.uninstall()
        if g.tree() != before:
            fails.append(f"{name}: uninstall did not restore the files")
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
    every language file loads, WeiDU writes the same strings from it into dialog.tlk as a plain
    reading (line ends LF, as in the games' own strings), and it has every @N the tp2 and tpa
    files use."""
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
        body = "LOAD_TRA ~cbprtest/lang.tra~\n" + "".join(
            f"OUTER_SET r = RESOLVE_STR_REF (@{n})\nPRINT ~RESULT TRA {n} %r%~\n" for n in entries)
        g = fg.FakeGame(work / f"tra_{tra.parent.name}", weidu, body)
        (g.root / "cbprtest/lang.tra").write_bytes(tra.read_bytes())
        out = g.install()
        refs = dict(r.split() for r in g.results(out, "TRA"))
        tlk = fg.tlk_entries(g.read("lang/en_us/dialog.tlk")) if fg.installed_ok(out) else []
        got = {n: tlk[int(ref)][0] for n, ref in refs.items() if int(ref) < len(tlk)}
        want = {n: s.replace("\r\n", "\n") for n, s in entries.items()}
        if not fg.installed_ok(out) or got != want:
            bad = sorted(n for n in want if got.get(n) != want[n])
            fails.append(f"{tra.parent.name}/{tra.name}: dialog.tlk differs from a plain reading for @{bad}: "
                         f"{[(got.get(n), want[n]) for n in bad[:2]]!r}")
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

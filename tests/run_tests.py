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
import struct
import subprocess
import sys
import tempfile
import zlib
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


# --- The look block on top of the world scripts ----------------------------------------

# Just the IDS entries the scripts use, with the EE games' signatures (EEex_LuaTrigger: EEex's).
SCRIPT_IDS = {
    "TRIGGER.IDS": ["0x400F Global(S:Name*,S:Area*,I:Value*)", "0x4017 Race(O:Object*,I:Race*Race)",
                    "0x4037 StateCheck(O:Object*,I:State*State)", "0x4043 InParty(O:Object*)",
                    "0x40E2 CheckSpellState(O:Object*,I:State*splstate)", "0x410E EEex_LuaTrigger(S:Chunk*)"],
    "ACTION.IDS": ["30 SetGlobal(S:Name*,S:Area*,I:Value*)", "36 Continue()", "160 ApplySpellRES(S:RES*,O:Target)"],
    "OBJECT.IDS": ["0 Nothing", "1 Myself"] + [f"{20 + n} Player{n}" for n in range(1, 7)],
    "STATE.IDS": ["0x00000FC0 STATE_REALLY_DEAD"],
    "RACE.IDS": ["1 HUMAN", "2 ELF", "111 HOBGOBLIN"],
}
OTHER_BLOCK = """IF
  Global("OTHER_MOD_{n}","GLOBAL",0)
THEN
  RESPONSE #100
    SetGlobal("OTHER_MOD_{n}","GLOBAL",1)
END
"""
LOOK_BAF = MOD / "hobgoblin/race_look.baf"
EW_TP2 = r"""OUTER_SET hg_splstate = 195
LAF hg_extend_world_scripts STR_VAR baf = ~cbprtest/race_look.baf~ RET count END
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
    """The shipped race_look.baf, its marker state filled in, goes on top of each world
    script the campaigns run (once, also when named twice), in front of the blocks already
    there; named scripts the game lacks are skipped and other scripts stay as they are;
    BALDUR.BCS without a CAMPAIGN.2DA; uninstall restores the override folder byte for byte."""
    ours = LOOK_BAF.read_text(encoding="ascii").replace("%hg_splstate%", "195")
    if "%" in ours:
        return [f"race_look.baf uses a variable this test does not fill in: {ours}"]
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
        (g.root / "cbprtest/race_look.baf").write_bytes(LOOK_BAF.read_bytes())
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


@test
def shipped_weapon_art(work, weidu):
    """The art in hobgoblin/weapons is the tool's own drawing: one BAMC per group art.tpa names
    and sprite file, no palette (all zero), no colour but the tool's wood and metal and the
    transparent 0, the same cycles in every group's file for a sprite file, and art.tpa's
    geometry sums for each sprite file the art was drawn along."""
    folder = MOD / "hobgoblin/weapons"
    if not (folder / "art.tpa").is_file():
        return ["no hobgoblin/weapons/art.tpa"]
    tpa = (folder / "art.tpa").read_text(encoding="ascii")
    found = re.search(r"OUTER_SPRINT hg_art_groups ~([^~]*)~", tpa)
    groups = found.group(1).split() if found else []
    fails = [] if sorted(groups) == sorted(art.GROUPS) else [f"art.tpa groups {groups}, want {list(art.GROUPS)}"]
    want = {f"{g}_{sfx.lower()}.bam" for g in groups for sfx in art.SFX}
    have = {p.name for p in folder.iterdir()} - {"art.tpa"}
    if have != want:
        fails.append(f"files: missing {sorted(want - have)}, extra {sorted(have - want)}")
    colours = {0, art.WOOD_HI, art.WOOD, art.WOOD_DARK, art.WOOD_CAP,
               art.MET_HI, art.MET_EDGE, art.MET, art.MET_DARK, art.MET_LINE}
    cycle_sizes = {}
    for name in sorted(want & have):
        data = (folder / name).read_bytes()
        if data[:8] != b"BAMCV1  ":
            fails.append(f"{name}: no BAMC")
            continue
        frames, cycles, _, palette = fg.read_bam(zlib.decompress(data[12:]))
        if any(palette):
            fails.append(f"{name}: has a palette")
        if extra := sorted(set().union(*(set(f[4]) for f in frames)) - colours):
            fails.append(f"{name}: colours {extra}")
        cycle_sizes.setdefault(name.split("_")[1], set()).add(tuple(count for count, _ in cycles))
    fails += [f"{sfx}: the groups' cycles differ" for sfx, sizes in sorted(cycle_sizes.items()) if len(sizes) > 1]
    for n in (1, 2):
        block = re.search(rf"hg_art_geo{n} BEGIN(.*?)END", tpa, re.S)
        sums = dict(re.findall(r"(\w+) => (\d+)", block.group(1))) if block else {}
        if sorted(sums) != sorted(art.SOURCES):
            fails.append(f"hg_art_geo{n} lists {sorted(sums)}, want {sorted(art.SOURCES)}")
    return fails


@test
def missing_weapon_art(work, weidu):
    """Without the weapon art (an incompletely unpacked mod) the component stops with its
    message before it changes any game file, and is not installed."""
    sprites = {name: creature_bam()[0] for name in ("mhobg1.bam", "mhobsg1.bam", "mhobbg1.bam")}
    g = fg.FakeGame(work / "noart", weidu, "", override={"8100.ini": b"[general]\r\n", **sprites},
                    files=fg.eeex_files())
    shutil.copy(REPO / "setup-chriz-bg-playable-races.tp2", g.root)
    shutil.copytree(MOD, g.root / MOD.name, ignore=shutil.ignore_patterns("weapons", "backup"), dirs_exist_ok=True)
    game_files = lambda: {k: v for k, v in g.tree().items()  # noqa: E731
                          if not k.startswith(("chriz-bg-playable-races/", "setup-chriz-bg-playable-races"))}
    before = game_files()
    proc = subprocess.run([weidu, "setup-chriz-bg-playable-races.tp2", "--no-auto-tp2", "--noautoupdate",
                           "--game", str(g.root), "--language", "0", "--use-lang", "en_US", "--force-install", "100",
                           "--no-exit-pause", "--log", "weidu-noart.debug"],
                          cwd=g.root, stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    out = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    fails = []
    if "weapon art (chriz-bg-playable-races/hobgoblin/weapons) is missing" not in out or not fg.failed(out):
        fails.append(f"no stop with the missing-art message: {out[-600:]}")
    if game_files() != before:
        fails.append("game files changed")
    log = g.root / "weidu.log"
    if log.is_file() and "chriz-bg-playable-races" in log.read_text(encoding="latin-1").lower():
        fails.append("the component is in WeiDU.log")
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


# --- The race in character creation ---------------------------------------------------------

OF_TP2 = r"""LAF hg_offer_race INT_VAR race = 111 name_ref = 900 desc_ref = 901 upper_ref = 902 bio_ref = 903
  STR_VAR label = ~HOBGOBLIN~ RET tables found END
PRINT ~RESULT OF %tables% %found%~
"""
OF_CAMPAIGN = fg.make_2da(["WORLDSCRIPT", "SAVE_DIR", "RACETEXT"],
                          [("SOA", ["BALDUR", "save", "RACETEXT"]), ("TOB", ["BALDUR25", "save", "RACETEXT"]),
                           ("BG1", ["BALDUR", "save", "BGRACTXT"]), ("SOD", ["BDBALDUR", "save", "SODRACE"]),
                           ("BP1", ["BALDUR", "bpsave", "*"]), ("TUT", ["BALDUR", "save", "bgractxt"])], "*")
# Vanilla BG:EE and BG2:EE 2.7: the columns, no rows.
OF_CAMPAIGN_EMPTY = fg.make_2da(["WORLDSCRIPT", "SAVE_DIR", "CLASTEXT", "RACETEXT"], [], "*")


def of_table(bio):
    """A race table: human (biography `bio`), half-orc, tiefling (not offered)."""
    return fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", bio]), ("HALF_ORC", ["7", "16", "26", "36", "46"]),
                                   ("TIEFLING", ["153", "17", "-1", "37", "-1"])])


@test
def offer_race(work, weidu):
    """The row goes into each race table the campaigns name (any letter case, once each) and
    RACETEXT.2DA, if the game has them, with its description; its biography only where the human
    has one. A table with a row for the race already gets none (counted as found, not as added);
    uninstall restores the files."""
    eet = {"CAMPAIGN.2DA": OF_CAMPAIGN, "RACETEXT.2DA": of_table("-1"), "BGRACTXT.2DA": of_table("215895"),
           "SODRACE.2DA": of_table("265359")}
    taken = {t: fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HOB", ["111", "5", "6", "7", "8"])])
             for t in ("RACETEXT.2DA", "BGRACTXT.2DA", "SODRACE.2DA")}
    cases = {  # name: (resources, rows {table: biography}, tables found)
        "eet": (eet, {"RACETEXT": "-1", "BGRACTXT": "903", "SODRACE": "903"}, 3),
        "vanilla": ({"CAMPAIGN.2DA": OF_CAMPAIGN_EMPTY, "RACETEXT.2DA": of_table("555")}, {"RACETEXT": "903"}, 1),
        "no_campaign": ({"RACETEXT.2DA": of_table("-1")}, {"RACETEXT": "-1"}, 1),
        "missing_table": ({k: v for k, v in eet.items() if k != "SODRACE.2DA"},
                          {"RACETEXT": "-1", "BGRACTXT": "903"}, 2),
        "taken": ({"CAMPAIGN.2DA": OF_CAMPAIGN, **taken}, {}, 3),
    }
    fails = []
    for name, (res, rows, found) in cases.items():
        g = fg.FakeGame(work / f"of_{name}", weidu, OF_TP2, biff=res)
        before = g.tree()
        out = g.install()
        got = g.results(out, "OF")
        if not fg.installed_ok(out) or got != [f"{len(rows)} {found}"]:
            fails.append(f"{name}: results {got}: {out[-800:]}")
            continue
        for tb in ("RACETEXT", "BGRACTXT", "SODRACE"):
            path = find_ci(g.root / "override", f"{tb}.2da")
            if tb not in rows:
                if path is not None:
                    fails.append(f"{name}: {tb}.2DA was written")
                continue
            _, body = fg.table(path.read_bytes()) if path else (None, {})
            if body.get("HOBGOBLIN") != ["111", "900", "901", "902", rows[tb]]:
                fails.append(f"{name}: {tb} row {body.get('HOBGOBLIN')}")
        g.uninstall()
        if g.tree() != before:
            fails.append(f"{name}: uninstall did not restore the files")
    return fails


# --- Race tables, line by line ---------------------------------------------------------------

def raw_2da(lines, eol="\r\n", final=True):
    """A 2DA file from its lines as given (no padding), for layouts make_2da does not write."""
    return (eol.join(lines) + (eol if final else "")).encode("ascii")


def grid(data):
    """A 2DA table as (default, column names, rows): each row label (upper case; the first row of
    that label) with its entries by column name. A short row lacks the entries it does not have;
    words beyond the header are left out."""
    lines = data.decode("latin-1").splitlines()
    cols = lines[2].split()
    rows = {}
    for ln in lines[3:]:
        w = ln.split()
        if w and w[0].upper() not in rows:
            rows[w[0].upper()] = dict(zip(cols, w[1:]))
    return (lines[1].split() or [""])[0], cols, rows


def words_by_label(data):
    """{row label as written: its other words} for each data line, and how many lines are blank."""
    lines = data.decode("latin-1").splitlines()
    return {ln.split()[0]: ln.split()[1:] for ln in lines[3:] if ln.split()}, sum(1 for ln in lines if not ln.split())


RW_TP2 = r"""COPY_EXISTING ~test.2da~ ~override~
  LPF cbpr_add_race_row STR_VAR label = ~HOBGOBLIN~ base = ~HALFORC~ values = ~%s~ RET added taken missing END
  PATCH_PRINT ~RESULT RW %%added%% %%taken%% [%%missing%%]~
BUT_ONLY
"""
AB_COLS = ["MOD_STR", "MOD_DEX", "MOD_CON", "MOD_INT", "MOD_WIS", "MOD_CHR"]
AB_ROWS = [("HUMAN", ["0", "0", "0", "0", "0", "0"]), ("HALFORC", ["1", "0", "1", "-2", "0", "0"]),
           ("DWARF", ["0", "-1", "1", "0", "0", "-1"])]


@test
def race_rows(work, weidu):
    """The race's row goes to the end of the table, every other byte kept: each column gets the
    value given for it (column names in any letter case and order, among other columns), else the
    base row's entry (the first row of that label, in any letter case), else the default value
    (also where the base row is short or missing); the line end follows the table's (CR LF or LF,
    also without a final line end). Values for columns the table lacks are reported; a table with
    a row of that label already stays as it was."""
    vals = "MOD_CON=1 mod_wis=-1 MOD_CHR=-1"
    want = ["HOBGOBLIN", "1", "0", "1", "-2", "-1", "-1"]
    cases = {  # name: (table, values, result, words of the new last line, or None: unchanged)
        "basic": (fg.make_2da(AB_COLS, AB_ROWS, "0"), vals, "1 0 []", want),
        "other_order": (fg.make_2da(["EXTRA", "MOD_CHR", "MOD_STR", "MOD_DEX", "MOD_CON", "MOD_INT", "MOD_WIS"],
                                    [("HUMAN", ["5", "0", "0", "0", "0", "0", "0"]),
                                     ("halforc", ["7", "0", "1", "0", "1", "-2", "0"])], "0"),
                        vals, "1 0 []", ["HOBGOBLIN", "7", "-1", "1", "0", "1", "-2", "-1"]),
        "short_base": (raw_2da(["2DA V1.0", "9", "  " + " ".join(AB_COLS), "HUMAN 0 0 0 0 0 0", "HALFORC 1 0 1"]),
                       vals, "1 0 []", ["HOBGOBLIN", "1", "0", "1", "9", "-1", "-1"]),
        "no_base": (fg.make_2da(AB_COLS, AB_ROWS[:1], "0"), vals, "1 0 []",
                    ["HOBGOBLIN", "0", "0", "1", "0", "-1", "-1"]),
        "missing_column": (fg.make_2da(AB_COLS, AB_ROWS, "0"), vals + " MIN_CON=11", "1 0 [ MIN_CON]", want),
        "lf_no_final_eol": (raw_2da(["2DA V1.0", "0", "  " + " ".join(AB_COLS), "HUMAN 0 0 0 0 0 0",
                                     "HALFORC 1 0 1 -2 0 0"], eol="\n", final=False), vals, "1 0 []", want),
        "header_only": (fg.make_2da(AB_COLS, [], "3"), vals, "1 0 []", ["HOBGOBLIN", "3", "3", "1", "3", "-1", "-1"]),
        "taken": (fg.make_2da(AB_COLS, AB_ROWS + [("hobgoblin", ["9"] * 6)], "0"), vals, "0 1 []", None),
    }
    fails = []
    for name, (table, values, result, words) in cases.items():
        g = fg.FakeGame(work / f"rw_{name}", weidu, RW_TP2 % values, biff={"TEST.2DA": table})
        out = g.install()
        got = g.results(out, "RW")
        path = find_ci(g.root / "override", "test.2da")
        if not fg.installed_ok(out) or got != [result]:
            fails.append(f"{name}: results {got}, want {result}: {out[-600:]}")
        elif words is None:
            if path is not None:
                fails.append(f"{name}: the table was written")
        else:
            data = path.read_bytes() if path else b""
            eol = b"\n" if name == "lf_no_final_eol" else b"\r\n"
            head = table if table.endswith(b"\n") else table + eol
            new = [ln.split() for ln in data.decode("latin-1").splitlines() if ln.split()][-1:]
            if not data.startswith(head) or not data.endswith(eol) or (eol == b"\n" and b"\r" in data):
                fails.append(f"{name}: other bytes or the line end changed: {data[-90:]!r}")
            elif new != [words]:
                fails.append(f"{name}: new row {new}, want {words}")
    return fails


CL_TP2 = r"""COPY_EXISTING ~test.2da~ ~override~
  LPF cbpr_add_race_column STR_VAR label = ~HOBGOBLIN~ base = ~HALFORC~ values = ~%s~ RET added taken missing END
  PATCH_PRINT ~RESULT CL %%added%% %%taken%% [%%missing%%]~
BUT_ONLY
"""
CR_COLS = ["HUMAN", "ELF", "HALFORC"]
CR_ROWS = [("MAGE", ["1", "1", "0"]), ("FIGHTER", ["1", "1", "1"]), ("SHADOWDANCER", ["1", "1", "1"]),
           ("DUALCLASS", ["1", "0", "0"])]


@test
def race_columns(work, weidu):
    """The race's column goes to the end of the header and of every row, the rest of each line
    kept: each row gets the value given for it (row names in any letter case), else its entry in
    the base column (the first of that name, wherever it is), else the default value. A short row
    first gets the default value for each entry it lacks; a row longer than the header gets the
    new entry right behind its last column; blank lines and LF line ends stay. Values for rows the
    table lacks are reported; a table with a column of that name already stays as it was."""
    vals = "dualclass=1 PALADIN=5"
    cases = {  # name: (table, values, result, {row label: words after it}, or None: unchanged)
        "basic": (fg.make_2da(CR_COLS, CR_ROWS, "0"), vals, "1 0 [ PALADIN]",
                  {"MAGE": ["1", "1", "0", "0"], "FIGHTER": ["1", "1", "1", "1"],
                   "SHADOWDANCER": ["1", "1", "1", "1"], "DUALCLASS": ["1", "0", "0", "1"]}),
        "short_long_blank": (raw_2da(["2DA V1.0", "0", "  HUMAN ELF HALFORC", "MAGE 1 1 0", "", "PALADIN 1",
                                      "MONK 1 1 1 9", "dualclass 1 0 0"], eol="\n"), vals, "1 0 []",
                             {"MAGE": ["1", "1", "0", "0"], "PALADIN": ["1", "0", "0", "5"],
                              "MONK": ["1", "1", "1", "1", "9"], "dualclass": ["1", "0", "0", "1"]}),
        "base_elsewhere": (fg.make_2da(["CLASS", "HALFORC", "HUMAN"], [("16384", ["MAGE", "1", "1"]),
                                                                      ("0x00000040", ["ABJURER", "0", "1"])], "1"),
                           "", "1 0 []", {"16384": ["MAGE", "1", "1", "1"], "0x00000040": ["ABJURER", "0", "1", "0"]}),
        "kit_tables": (fg.make_2da(CR_COLS, [("MAGE", ["K_M_H", "K_M_E", "K_M_HO"]),
                                             ("THIEF", ["K_T_H", "K_T_E", "K_T_HO"])], "*"), "", "1 0 []",
                       {"MAGE": ["K_M_H", "K_M_E", "K_M_HO", "K_M_HO"], "THIEF": ["K_T_H", "K_T_E", "K_T_HO", "K_T_HO"]}),
        "no_base": (fg.make_2da(["HUMAN", "ELF"], [(n, v[:2]) for n, v in CR_ROWS], "0"), vals, "1 0 [ PALADIN]",
                    {"MAGE": ["1", "1", "0"], "FIGHTER": ["1", "1", "0"], "SHADOWDANCER": ["1", "1", "0"],
                     "DUALCLASS": ["1", "0", "1"]}),
        "taken": (fg.make_2da(CR_COLS + ["hobgoblin"], [(n, v + ["1"]) for n, v in CR_ROWS], "0"), vals, "0 1 []", None),
    }
    fails = []
    for name, (table, values, result, rows) in cases.items():
        g = fg.FakeGame(work / f"cl_{name}", weidu, CL_TP2 % values, biff={"TEST.2DA": table})
        out = g.install()
        got = g.results(out, "CL")
        path = find_ci(g.root / "override", "test.2da")
        if not fg.installed_ok(out) or got != [result]:
            fails.append(f"{name}: results {got}, want {result}: {out[-600:]}")
            continue
        if rows is None:
            if path is not None:
                fails.append(f"{name}: the table was written")
            continue
        data = path.read_bytes() if path else b""
        old_lines, new_lines = table.decode("latin-1").splitlines(), data.decode("latin-1").splitlines()
        body, blanks = words_by_label(data)
        if new_lines[:2] != old_lines[:2] or new_lines[2].split() != old_lines[2].split() + ["HOBGOBLIN"]:
            fails.append(f"{name}: head {new_lines[:3]}")
        if body != rows or blanks != words_by_label(table)[1]:
            fails.append(f"{name}: rows {body}, blank lines {blanks}")
        if (b"\r" in data) != (b"\r" in table):
            fails.append(f"{name}: line ends changed")
    return fails


EN_TP2 = r"""COPY_EXISTING - ~test.2da~ ~override~
  LPF cbpr_2da_entry STR_VAR row = ~%s~ column = ~%s~ RET value found END
  PATCH_PRINT ~RESULT EN %%found%% [%%value%%]~
"""


@test
def entry_2da(work, weidu):
    """An entry by row and column label, in any letter case; the default value where the row or
    the column is missing (not found) or the row is too short (found)."""
    table = raw_2da(["2DA V1.0", "7", "  OPEN_LOCKS FIND_TRAPS SET_TRAPS", "HUMAN 10 5 0", "GNOME 15 15",
                     "HUMAN 99 99 99"])
    asks = [("HUMAN", "OPEN_LOCKS"), ("human", "find_traps"), ("GNOME", "SET_TRAPS"), ("TIEFLING", "OPEN_LOCKS"),
            ("HUMAN", "NOPE")]
    want = ["1 [10]", "1 [5]", "1 [7]", "0 [7]", "0 [7]"]
    g = fg.FakeGame(work / "en", weidu, "".join(EN_TP2 % a for a in asks), biff={"TEST.2DA": table})
    out = g.install()
    got = g.results(out, "EN")
    return [] if fg.installed_ok(out) and got == want else [f"{got}, want {want}: {out[-600:]}"]


# --- The engine code the race hook redirects ----------------------------------------------------

def hook_pattern():
    """The pattern the race hook's loader file gives."""
    return re.search(r"^Pattern=([0-9A-Fa-f?]+)\s*$", (MOD / "race/CBPRRACE.db").read_text(encoding="ascii"),
                     re.M).group(1)


def code_of(pattern, fill=0x00, change=None):
    """Bytes matching `pattern`: its wildcards filled with `fill`; `change` (index, byte) alters one."""
    out = bytearray(fill if pattern[i:i + 2] == "??" else int(pattern[i:i + 2], 16)
                    for i in range(0, len(pattern), 2))
    if change:
        out[change[0]] = change[1]
    return bytes(out)


def pe64(text, data=b"", text_exec=True):
    """A minimal 64-bit PE file with two sections: .text (executable unless `text_exec` is False)
    holding `text`, and .data holding `data`."""
    opt = 0xF0
    head = bytearray(0x400)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x40)
    head[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HH", head, 0x44, 0x8664, 2)
    struct.pack_into("<H", head, 0x54, opt)
    struct.pack_into("<H", head, 0x58, 0x20B)
    for i, (name, start, size, flags) in enumerate([(b".text", 0x400, len(text), 0x60000020 if text_exec else 0x40000040),
                                                    (b".data", 0x400 + len(text), len(data), 0xC0000040)]):
        o = 0x40 + 24 + opt + 40 * i
        head[o:o + 8] = name.ljust(8, b"\0")
        struct.pack_into("<IIII", head, o + 8, size, 0x1000 * (i + 1), size, start)
        struct.pack_into("<I", head, o + 36, flags)
    return bytes(head) + text + data


CP_TP2 = r"""LAF cbpr_code_pattern_count STR_VAR exe = ~%s~ pattern = ~%s~ RET count offset error END
PRINT ~RESULT CP %s %%count%% %%offset%% %%error%%~
"""


@test
def code_pattern(work, weidu):
    """The hook's pattern counts where all its fixed bytes match, whatever the wildcard bytes are
    (also %, ~ and 0), in executable sections only, up to a section's end; one changed fixed byte
    is no match. A pattern with %, ~ or 0 among its fixed bytes is still found. No file, a file
    that is no 64-bit PE, a pattern that is not hex and ??, and one without 8 fixed bytes in a row
    are told apart and count nothing."""
    pat = hook_pattern()
    code = code_of(pat)
    pad = b"\xcc" * 48
    special = "41424344257E464748494A4B4C4D4E4F2550??51"
    files = {  # name: (file bytes or None, pattern, want "count offset error")
        "once": (pe64(pad + code + pad), pat, f"1 {0x400 + 48} 0"),
        "twice": (pe64(pad + code + pad + code), pat, f"2 {0x400 + 96 + len(code)} 0"),
        "none": (pe64(pad * 3), pat, "0 -1 0"),
        "near_miss": (pe64(code_of(pat, change=(len(code) - 1, 0xE0)) + pad + code), pat, f"1 {0x400 + len(code) + 48} 0"),
        "wild_specials": (pe64(pad + code_of(pat, fill=0x25) + code_of(pat, fill=0x7E)), pat,
                          f"2 {0x400 + 48 + len(code)} 0"),
        "at_section_end": (pe64(pad + code, data=code[:8]), pat, f"1 {0x400 + 48} 0"),
        "data_only": (pe64(pad, data=code), pat, "0 -1 0"),
        "not_executable": (pe64(pad + code, text_exec=False), pat, "0 -1 0"),
        "special_fixed": (pe64(pad + code_of(special) + pad), special, f"1 {0x400 + 48} 0"),
        "no_file": (None, pat, "0 -1 1"),
        "not_pe": (b"MZ" + bytes(2000), pat, "0 -1 2"),
        "bad_pattern": (pe64(pad), "4053G0", "0 -1 3"),
        "odd_pattern": (pe64(pad), "40534", "0 -1 3"),
        "short_runs": (pe64(pad), "40534883EC20??410FB6C0488B??", "0 -1 4"),
    }
    g = fg.FakeGame(work / "cp", weidu, "".join(CP_TP2 % (f"cbprtest/{n}.exe", p, n) for n, (_, p, _) in files.items()))
    for n, (data, _, _) in files.items():
        if data is not None:
            (g.root / f"cbprtest/{n}.exe").write_bytes(data)
    out = g.install()
    got = dict(r.split(" ", 1) for r in g.results(out, "CP"))
    fails = [f"{n}: {got.get(n)}, want {w}" for n, (_, _, w) in files.items() if got.get(n) != w]
    return fails if fg.installed_ok(out) else [f"install failed: {out[-800:]}"]


# --- The race hook ----------------------------------------------------------------------------

RG_TP2 = r"""LAF cbpr_register_race INT_VAR id = %d bio = 900 STR_VAR label = ~%s~ RET error END
PRINT ~RESULT RG %%error%%~
"""
RG_COLS = ["ID", "BIOGRAPHY"]


@test
def register_race(work, weidu):
    """The race goes into the hook's race list (made when there is none), and the hook's Lua and
    pattern file into the game, byte for byte; a race listed already with the same label is not
    listed twice. A race the hook cannot label (outside 8-255, or 153), a label that is not a word
    of capital letters, digits and _, a race or label the list gives to another, and a list without
    an ID column change nothing. Uninstall restores the game."""
    other = fg.make_2da(RG_COLS, [("GOBLIN", ["161", "5"])])
    cases = {  # name: (race list or None, id, label, error, rows wanted {label: [id, bio]})
        "new": (None, 111, "HOBGOBLIN", "0", {"HOBGOBLIN": ["111", "900"]}),
        "second_race": (other, 111, "HOBGOBLIN", "0", {"GOBLIN": ["161", "5"], "HOBGOBLIN": ["111", "900"]}),
        "listed_already": (fg.make_2da(RG_COLS, [("HOBGOBLIN", ["111", "900"])]), 111, "HOBGOBLIN", "0",
                           {"HOBGOBLIN": ["111", "900"]}),
        "label_elsewhere": (fg.make_2da(RG_COLS, [("HOBGOBLIN", ["112", "5"])]), 111, "HOBGOBLIN", "3", None),
        "race_elsewhere": (fg.make_2da(RG_COLS, [("HOB", ["111", "5"])]), 111, "HOBGOBLIN", "3", None),
        "race_7": (None, 7, "HOBGOBLIN", "1", None),
        "race_153": (None, 153, "HOBGOBLIN", "1", None),
        "race_256": (None, 256, "HOBGOBLIN", "1", None),
        "digits_underscore": (None, 112, "HOB_GOBLIN2", "0", {"HOB_GOBLIN2": ["112", "900"]}),
        "lower_case": (None, 111, "Hobgoblin", "2", None),
        "one_lower_letter": (None, 111, "HOBGOBLIn", "2", None),
        "two_words": (None, 111, "HOB GOBLIN", "2", None),
        "no_id_column": (fg.make_2da(["RACE", "BIOGRAPHY"], [("GOBLIN", ["161", "5"])]), 111, "HOBGOBLIN", "4", None),
    }
    fails = []
    for name, (table, rid, label, error, rows) in cases.items():
        g = fg.FakeGame(work / f"rg_{name}", weidu, RG_TP2 % (rid, label),
                        override={"CBPRRACE.2DA": table} if table else None,
                        files={"EEex_scripts/extra_pattern_dbs/v2.7.3.0.db": b"[X]\r\nPattern=90\r\n"})
        before = g.tree()
        out = g.install()
        got = g.results(out, "RG")
        if not fg.installed_ok(out) or got != [error]:
            fails.append(f"{name}: results {got}, want {error}: {out[-600:]}")
            continue
        if rows is None:
            if g.tree() != before:
                fails.append(f"{name}: files changed")
            continue
        _, _, body = grid(g.read("override/CBPRRACE.2DA"))
        if {k: [v.get("ID"), v.get("BIOGRAPHY")] for k, v in body.items()} != rows:
            fails.append(f"{name}: race list {body}")
        for src, dst in (("race/M_CBPRRC.lua", "override/M_CBPRRC.lua"),
                         ("race/CBPRRACE.db", "EEex_scripts/extra_pattern_dbs/CBPRRACE.db")):
            if not (g.root / dst).is_file() or g.read(dst) != (MOD / src).read_bytes():
                fails.append(f"{name}: {dst} is not the mod's {src}")
        g.uninstall()
        if g.tree() != before:
            fails.append(f"{name}: uninstall did not restore the game")
    return fails


@test
def hook_files(work, weidu):
    """The race hook's files agree: its Lua asks EEex's loader for the one label the pattern file
    defines, the pattern file tells the loader not to cache addresses in it, the installer reads its
    pattern, and every Lua function the world script calls is one the hook's Lua defines."""
    db = (MOD / "race/CBPRRACE.db").read_text(encoding="ascii")
    lua = (MOD / "race/M_CBPRRC.lua").read_text(encoding="utf-8")
    baf = LOOK_BAF.read_text(encoding="ascii")
    fails = []
    labels = re.findall(r"^\[([^\]]+)\]", db, re.M)
    if len(labels) != 1 or "NoCache=1" not in db.splitlines():
        fails.append(f"pattern file: labels {labels}, NoCache=1 {'NoCache=1' in db.splitlines()}")
    elif f'EEex_LabelDefault("{labels[0]}"' not in lua:
        fails.append(f"the Lua does not ask for {labels[0]}")
    called = set(re.findall(r'EEex_LuaTrigger\("return (\w+)\(', baf))
    if not called:
        fails.append("the world script calls no Lua")
    fails += [f"the Lua does not define {fn}" for fn in sorted(called) if f"function {fn}(" not in lua]
    g = fg.FakeGame(work / "hookfiles", weidu, "LAF cbpr_race_hook_pattern RET pattern END\nPRINT ~RESULT HP %pattern%~\n")
    out = g.install()
    if g.results(out, "HP") != [hook_pattern()]:
        fails.append(f"the installer reads {g.results(out, 'HP')}")
    return fails


HO_TP2 = r"""LAF cbpr_race_hook_pattern STR_VAR folder = ~othermod/race~ RET pattern END
PRINT ~RESULT HP %pattern%~
LAF cbpr_register_race INT_VAR id = 120 bio = 5 STR_VAR label = ~ORC~ folder = ~othermod/race~ RET error END
PRINT ~RESULT RG %error%~
"""


@test
def hook_files_other_mod(work, weidu):
    """Another mod ships the hook's files in a folder of its own: the installer reads the pattern
    there and installs the hook's files from there, its race in the one race list."""
    g = fg.FakeGame(work / "hookother", weidu, HO_TP2,
                    override={"CBPRRACE.2DA": fg.make_2da(RG_COLS, [("HOBGOBLIN", ["111", "900"])])})
    shutil.copytree(g.root / "chriz-bg-playable-races/race", g.root / "othermod/race")
    shutil.rmtree(g.root / "chriz-bg-playable-races/race")
    out = g.install()
    if not fg.installed_ok(out) or g.results(out, "HP") != [hook_pattern()] or g.results(out, "RG") != ["0"]:
        return [f"results {g.results(out, 'HP')} {g.results(out, 'RG')}: {out[-600:]}"]
    fails = []
    _, _, body = grid(g.read("override/CBPRRACE.2DA"))
    if {k: [v.get("ID"), v.get("BIOGRAPHY")] for k, v in body.items()} != {"HOBGOBLIN": ["111", "900"],
                                                                          "ORC": ["120", "5"]}:
        fails.append(f"race list {body}")
    for src, dst in (("race/M_CBPRRC.lua", "override/M_CBPRRC.lua"),
                     ("race/CBPRRACE.db", "EEex_scripts/extra_pattern_dbs/CBPRRACE.db")):
        if not (g.root / dst).is_file() or g.read(dst) != (MOD / src).read_bytes():
            fails.append(f"{dst} is not the mod's {src}")
    return fails


# --- The hobgoblin's race tables (race.tpa) -----------------------------------------------------

RQ_COLS = ["MIN_STR", "MAX_STR", "MIN_DEX", "MAX_DEX", "MIN_CON", "MAX_CON", "MIN_INT", "MAX_INT", "MIN_WIS",
           "MAX_WIS", "MIN_CHR", "MAX_CHR"]
SK_COLS = ["PICK_POCKETS", "OPEN_LOCKS", "FIND_TRAPS", "MOVE_SILENTLY", "HIDE_IN_SHADOWS", "DETECT_ILLUSION",
           "SET_TRAPS"]
RD_TABLES = {
    "ABRACEAD.2DA": fg.make_2da(AB_COLS, AB_ROWS, "0"),
    "ABRACERQ.2DA": fg.make_2da(RQ_COLS, [("HUMAN", ["3", "18"] * 6), ("HALFORC", ["3", "18"] * 6)], "0"),
    "SKILLRAC.2DA": fg.make_2da(SK_COLS, [("HUMAN", ["15", "10", "5", "10", "5", "10", "0"]),
                                          ("HALFORC", ["15", "10", "10", "10", "5", "5", "0"])], "0"),
    "RACEFEAT.2DA": fg.make_2da(["VALUE"], [("ELF", ["1"]), ("HALFORC", ["1"]), ("GOBLIN", ["1"])], "0"),
    "CLSRCREQ.2DA": fg.make_2da(CR_COLS, CR_ROWS, "0"),
    "KITTABLE.2DA": fg.make_2da(CR_COLS, [("MAGE", ["K_M_H", "K_M_E", "K_M_HO"]), ("THIEF", ["K_T_H", "K_T_E", "K_T_HO"])], "*"),
    "MGSRCREQ.2DA": fg.make_2da(["CLASS", "HUMAN", "HALFORC"], [("16384", ["MAGE", "1", "1"]),
                                                               ("0x00000040", ["ABJURER", "1", "0"])], "1"),
    "RACETHAC.2DA": fg.make_2da(["LABEL", "HUMAN", "ELF", "HALFORC"], [("89", ["BASTARDSWORD", "0", "0", "0"]),
                                                                      ("90", ["LONGSWORD", "0", "1", "2"])], "0"),
    "RACECOLR.2DA": fg.make_2da(["HUMAN", "HALFORC"], [("HAIR", ["2", "112"]), ("SKIN", ["12", "15"])], "12"),
    "RACETEXT.2DA": fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HALF_ORC", ["7", "16", "26", "36", "46"])]),
}
RD_TP2 = r"""LOAD_TRA ~cbprtest/lang.tra~
OUTER_SET race_hob = 111
ACTION_DEFINE_ASSOCIATIVE_ARRAY hg_col BEGIN 3 => 19   6 => 7 END
INCLUDE ~chriz-bg-playable-races/hobgoblin/race.tpa~
"""
# The hobgoblin's entries in RD_TABLES: (table, row or column label, {label: entry}).
RD_WANT = [
    ("ABRACEAD", "row", {"MOD_STR": "0", "MOD_DEX": "0", "MOD_CON": "1", "MOD_INT": "0", "MOD_WIS": "-1", "MOD_CHR": "-1"}),
    ("ABRACERQ", "row", dict(zip(RQ_COLS, ["6", "18", "6", "18", "11", "18", "3", "18", "4", "18", "4", "18"]))),
    ("SKILLRAC", "row", dict(zip(SK_COLS, ["15", "15", "10", "20", "10", "10", "0"]))),
    ("RACEFEAT", "row", {"VALUE": "1"}),
    ("CLSRCREQ", "column", {"MAGE": "0", "FIGHTER": "1", "SHADOWDANCER": "1", "DUALCLASS": "1"}),
    ("KITTABLE", "column", {"MAGE": "K_M_HO", "THIEF": "K_T_HO"}),
    ("MGSRCREQ", "column", {"16384": "1", "0X00000040": "0"}),
    ("RACETHAC", "column", {"89": "0", "90": "2"}),
    ("RACECOLR", "column", {"HAIR": "7", "SKIN": "19"}),
]


def race_data_game(work, weidu, name, tables):
    g = fg.FakeGame(work / f"rd_{name}", weidu, RD_TP2, biff=tables)
    (g.root / "chriz-bg-playable-races/hobgoblin").mkdir(parents=True)
    shutil.copy(MOD / "hobgoblin/race.tpa", g.root / "chriz-bg-playable-races/hobgoblin/race.tpa")
    shutil.copy(MOD / "lang/english/setup.tra", g.root / "cbprtest/lang.tra")
    return g


def race_data_problems(g, want):
    problems = []
    for table, kind, entries in want:
        path = find_ci(g.root / "override", f"{table}.2da")
        if path is None:
            problems.append(f"{table}.2DA not written")
            continue
        _, cols, rows = grid(path.read_bytes())
        got = rows.get("HOBGOBLIN", {}) if kind == "row" else \
            {r: e.get("HOBGOBLIN") for r, e in rows.items() if r in entries}
        if {k: got.get(k) for k in entries} != entries:
            problems.append(f"{table}: {got}")
    return problems


@test
def race_data(work, weidu):
    """race.tpa gives HOBGOBLIN its entries in every race table the game has: the ability scores,
    the human's thief skills plus the race's, infravision, the half-orc's classes and kits, mage
    schools and racial THAC0 with dual-class allowed, and the hobgoblin's colours; a row in the race
    list of character creation (the biography where the human has one) and in the hook's race list,
    and the hook's files. Other mods' layouts work: columns in another order and other columns,
    other races, short rows, LF line ends, missing optional tables. Uninstall restores the game."""
    fails = []
    variations = dict(RD_TABLES)
    variations["ABRACEAD.2DA"] = fg.make_2da(["MOD_CHR", "MOD_WIS", "EXTRA", "MOD_INT", "MOD_CON", "MOD_DEX", "MOD_STR"],
                                             [("HUMAN", ["0"] * 7), ("HALFORC", ["0", "0", "8", "-2", "1", "0", "1"])], "0")
    variations["CLSRCREQ.2DA"] = raw_2da(["2DA V1.0", "0", "  HUMAN HALFORC TIEFLING ELF", "MAGE 1 1 1 1", "FIGHTER 1",
                                          "SHADOWDANCER 1 1 1 1", "DUALCLASS 1 0 0 0"], eol="\n")
    variations["RACEFEAT.2DA"] = fg.make_2da(["VALUE"], [("HALFORC", ["0"]), ("AASIMAR", ["1"])], "0")
    for t in ("MGSRCREQ.2DA", "RACETHAC.2DA"):
        del variations[t]
    variations.update({"CAMPAIGN.2DA": OF_CAMPAIGN, "BGRACTXT.2DA": of_table("215895"), "SODRACE.2DA": of_table("-1")})
    var_want = [w for w in RD_WANT if w[0] not in ("MGSRCREQ", "RACETHAC", "CLSRCREQ")]
    var_want.append(("CLSRCREQ", "column", {"MAGE": "1", "FIGHTER": "0", "SHADOWDANCER": "1", "DUALCLASS": "1"}))
    for name, tables, want, texts in (("base", RD_TABLES, RD_WANT, {"RACETEXT": True}),
                                      ("variations", variations, var_want,
                                       {"RACETEXT": True, "BGRACTXT": True, "SODRACE": False})):
        g = race_data_game(work, weidu, name, tables)
        before = g.tree()
        out = g.install()
        if not fg.installed_ok(out) or "WARNING" in out:
            fails.append(f"{name}: {out[-900:]}")
            continue
        fails += [f"{name}: {p}" for p in race_data_problems(g, want)]
        _, _, hook = grid(g.read("override/CBPRRACE.2DA"))
        bio = hook.get("HOBGOBLIN", {}).get("BIOGRAPHY")
        if hook.get("HOBGOBLIN", {}).get("ID") != "111" or not (bio or "").isdigit():
            fails.append(f"{name}: hook race list {hook}")
        for tb, with_bio in texts.items():
            _, _, rows = grid(find_ci(g.root / "override", f"{tb}.2da").read_bytes())
            row = rows.get("HOBGOBLIN", {})
            if row.get("ID") != "111" or not all(row.get(c, "").isdigit() for c in ("NAME", "DESCSTR", "UPPERCASE")) \
                    or row.get("BIOGRAPHY") != (bio if with_bio else "-1"):
                fails.append(f"{name}: {tb} row {row}")
        if not (g.root / "override/M_CBPRRC.lua").is_file() or \
                not (g.root / "EEex_scripts/extra_pattern_dbs/CBPRRACE.db").is_file():
            fails.append(f"{name}: the hook's files are missing")
        g.uninstall()
        if g.tree() != before:
            fails.append(f"{name}: uninstall did not restore the game")
    return fails


@test
def race_data_refused(work, weidu):
    """race.tpa stops, and the game is left as it was, where the race cannot work as described:
    a table of the ability scores without a column the race sets, a table with a HOBGOBLIN entry
    of another mod, a race list with a row for race 111 already. A lesser table without an entry the
    race sets (no DUALCLASS row) only warns."""
    rq = fg.make_2da([c for c in RQ_COLS if "CON" not in c], [("HALFORC", ["3", "18"] * 5)], "0")
    kits = fg.make_2da(CR_COLS + ["HOBGOBLIN"], [("MAGE", ["K_M_H", "K_M_E", "K_M_HO", "K_M_X"])], "*")
    text = fg.make_2da(RACE_COLS, [("HUMAN", ["1", "10", "20", "30", "40"]), ("HOB", ["111", "5", "6", "7", "8"])])
    cases = {  # name: (table replaced, its bytes, text wanted in the output, installed with a warning)
        "ability_column": ("ABRACERQ.2DA", rq, "ABRACERQ.2DA lacks MIN_CON MAX_CON", False),
        "taken": ("KITTABLE.2DA", kits, "KITTABLE.2DA has a HOBGOBLIN entry already", False),
        "race_text": ("RACETEXT.2DA", text, "has a row for race 111 or for HOBGOBLIN already", False),
        "no_dualclass": ("CLSRCREQ.2DA", fg.make_2da(CR_COLS, CR_ROWS[:3], "0"), "CLSRCREQ.2DA lacks DUALCLASS", True),
    }
    fails = []
    for name, (table, data, text, warns) in cases.items():
        g = race_data_game(work, weidu, f"x_{name}", {**RD_TABLES, table: data})
        before = g.tree()
        out = g.install()
        if text not in out:
            fails.append(f"{name}: no message {text!r}: {out[-700:]}")
        if warns:
            if "INSTALLED WITH WARNINGS" not in out:
                fails.append(f"{name}: not installed with a warning")
            g.uninstall()
        elif not fg.failed(out):
            fails.append(f"{name}: not stopped")
        if g.tree() != before:
            fails.append(f"{name}: game files changed")
    return fails


# --- The component's checks before it changes anything --------------------------------------------

def component_game(work, weidu, name, files=None, biff=None):
    """A fake game with the hobgoblin's sprites and the whole mod, for the real tp2."""
    sprites = {n: creature_bam()[0] for n in ("mhobg1.bam", "mhobsg1.bam", "mhobbg1.bam")}
    g = fg.FakeGame(work / name, weidu, "", override={"8100.ini": b"[general]\r\n", **sprites}, files=files, biff=biff)
    shutil.copy(REPO / "setup-chriz-bg-playable-races.tp2", g.root)
    shutil.copytree(MOD, g.root / MOD.name, ignore=shutil.ignore_patterns("backup"), dirs_exist_ok=True)
    return g


def install_component(g, tag):
    proc = subprocess.run([g.weidu, "setup-chriz-bg-playable-races.tp2", "--no-auto-tp2", "--noautoupdate",
                           "--game", str(g.root), "--language", "0", "--use-lang", "en_US", "--force-install", "100",
                           "--no-exit-pause", "--log", f"weidu-{tag}.debug"],
                          cwd=g.root, stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
    return (proc.stdout + proc.stderr).decode("utf-8", "replace")


@test
def component_checks(work, weidu):
    """The component needs EEex with the race hook's functions, pattern folder and script trigger,
    a race number the hook can label, and the engine code the hook redirects exactly once in
    Baldur.exe; without one of them it is not installed and no game file changes."""
    ids = {"RACE.IDS": b"IDS V1.0\r\n1 HUMAN\r\n111 HOBGOBLIN\r\n"}
    code = code_of(hook_pattern())
    good_exe = {"Baldur.exe": pe64(b"\xcc" * 32 + code + b"\xcc" * 32)}
    cases = {  # name: (files, biff, text wanted in the output)
        "no_eeex": ({}, ids, "which this game lacks. Install EEex"),
        "no_trigger": (fg.eeex_files(trigger=False), ids, "the script trigger EEex_LuaTrigger"),
        "no_functions": (fg.eeex_files(functions=False), ids, "the script trigger EEex_LuaTrigger"),
        "no_exe": (fg.eeex_files(), ids, "found 0 time(s), check 1"),
        "exe_without_code": ({**fg.eeex_files(), "Baldur.exe": pe64(b"\xcc" * 64)}, ids, "found 0 time(s), check 0"),
        "code_twice": ({**fg.eeex_files(), "Baldur.exe": pe64(code + code)}, ids, "found 2 time(s), check 0"),
        "race_153": ({**fg.eeex_files(), **good_exe}, {"RACE.IDS": b"IDS V1.0\r\n153 HOBGOBLIN\r\n"},
                     "gives HOBGOBLIN the number 153"),
    }
    fails = []
    for name, (files, biff, text) in cases.items():
        g = component_game(work, weidu, f"cc_{name}", files=files, biff=biff)
        game_files = lambda: {k: v for k, v in g.tree().items()  # noqa: E731
                              if not k.startswith(("chriz-bg-playable-races/", "setup-chriz-bg-playable-races"))}
        before = game_files()
        out = install_component(g, name)
        log = g.root / "weidu.log"
        if text not in out:
            fails.append(f"{name}: no message {text!r}: {out[-700:]}")
        if log.is_file() and "chriz-bg-playable-races" in log.read_text(encoding="latin-1").lower():
            fails.append(f"{name}: the component is in WeiDU.log")
        if game_files() != before:
            fails.append(f"{name}: game files changed")
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

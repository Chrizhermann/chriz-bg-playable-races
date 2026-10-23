# A race of its own with EEex

How this mod makes the hobgoblin a real race, and how another race (ours or another mod's) can
use the same hook. Status: prototype. Lab-tested on EET over BG2:EE 2.7.3.0 with EEex v1.2.0 and
v1.3.1; see [What is tested](#what-is-tested).

## Why a new race needs EEex

A race is a number in `RACE.IDS` (the hobgoblin is 111). The engine looks a race up in two ways:

| What | Keyed by | Tables |
|---|---|---|
| Names, description, biography | the race number | `RACETEXT.2DA`; per campaign the table in column `RACETEXT` of `CAMPAIGN.2DA` (EET: `RACETEXT`, `BGRACTXT`, `SODRACE`) |
| Rules | the race's **label**, from `CRuleTables::GetRaceString(race)` | see the table below |

`GetRaceString` is hardcoded: races 1-7 get `HUMAN`, `ELF`, `HALF_ELF`, `DWARF`, `HALFLING`,
`GNOME`, `HALFORC`; race 153 gets the elf's label; every other race gets an empty label. With an
empty label, every rules table gives its default value: character creation offers such a race
no class, and the race gets no thief skill bonus and no infravision, even from rows named
after it (lab runs 14b, 15c, 15d).

The rules tables the engine reads under the label (callers of `GetRaceString` in the
2.7.3.0 executable), and what the lab saw for race 111:

| Table | Races as | What it decides | Seen in the lab |
|---|---|---|---|
| `CLSRCREQ.2DA` | columns | the classes and multi-classes a race may take; row `DUALCLASS`: whether it may dual-class | the classes offered, the dual-class button (runs 17b, 18) |
| `KITTABLE.2DA` | columns | per class, the kit table `K_<class>_<race>` (half-orc thief: `K_T_HO`) | the kits offered (runs 17b, 18) |
| `ABRACEAD.2DA` | rows | ability score adjustments (`MOD_STR` ...) | the rolls (runs 17b, 18) |
| `ABRACERQ.2DA` | rows | ability score limits (`MIN_STR`, `MAX_STR`, ...) | the rolls (runs 17b, 18) |
| `SKILLRAC.2DA` | rows | thief skills by race | the skills in character creation and in the world (runs 17b, 18) |
| `RACEFEAT.2DA` | rows | racial features (`VALUE` 1: infravision) | infravision (runs 17b, 18c) |
| `RACECOLR.2DA` | columns | default `HAIR` and `SKIN` colours in character creation | the colours (run 17b) |
| `RACETHAC.2DA` | columns | racial to-hit bonuses with weapon types | not checked |

`MGSRCREQ.2DA` (mage schools, races as columns) has race columns too, but no caller of
`GetRaceString` reads it, and how the engine finds a race's column there is not established.
This mod gives the hobgoblin the half-orc's column anyway.

Two things to know about the ability tables (lab run 18, 3,000 rolls per race): the engine rolls
each score within `ABRACERQ` and then adds `ABRACEAD`, without limiting the sum again. The
half-orc's Intelligence (3-18, then -2) came out 1-16. So for Constitution 12-19 with
`MOD_CON` 1, the hobgoblin has `MIN_CON` 11 and `MAX_CON` 18.

Racial infravision sets a party member's `m_bInfravisionOn`, which `CGameSprite::AIUpdate`
recomputes from `STATE_INFRAVISION` (`op63`) and `RACEFEAT.2DA` under the label. In the lab it
was 1 only while that member was the only one selected, so check it that way.

## The hook

EEex can redirect an engine function. This mod's hook makes `GetRaceString` answer each race it
lists with that race's label and hands every other race to the original code. It consists of
three files, in the mod's folder `chriz-bg-playable-races/race`:

| File | Installed as | What it is |
|---|---|---|
| `CBPRRACE.2DA` | `override/CBPRRACE.2DA` | the race list: one row per race, the row label is the race's label, column `ID` its number, column `BIOGRAPHY` a string reference (or -1) |
| `CBPRRACE.db` | `EEex_scripts/extra_pattern_dbs/CBPRRACE.db` | the byte pattern by which EEex's loader finds `GetRaceString` at game start, as the label `CBPR-CRuleTables::GetRaceString` |
| `M_CBPRRC.lua` | `override/M_CBPRRC.lua` | the hook, installed when the game state is ready |

At game start `M_CBPRRC.lua`:

1. reads `CBPRRACE.2DA` and keeps each row whose race can have a label of its own (8-255, not
   153), whose label is capital letters, digits and `_`, and whose race and label no earlier row
   has;
2. asks EEex's loader for the function, checks its first six bytes (`push rbx; sub rsp, 20h`),
   and finds the engine's `CString(const char *)` constructor among the function's own calls;
3. redirects the function: one comparison per listed race, which then gets its label, and
   every other race goes to the original code;
4. prints the result to the console, e.g.
   `Chriz BG Playable Races: race hook active for HOBGOBLIN (111) at 0x140246440`, and keeps it
   in `CBPR_RaceHook.Status` (`CBPR_RaceHook.installed` is true when active).

It also gives each listed race with a biography an entry in EET's `bioRaceData`, which EET's
character creation uses for the race part of the biography (a copy of the human's entry with the
race's biography in place of each of the human's), and it defines
`CBPR_HasCharacterAnimation(slot)` for world scripts (see [The look](#the-look)).

**One hook for every race.** Two hooks on the same function cannot both work: the second would
find the first one's jump there and stay off. So a mod that adds a race should add its row to
`CBPRRACE.2DA` and ship the three files unchanged (copies of the same version are identical). A
later install overwrites the Lua and pattern files with its copy and adds its row to the list.

## Adding a race

The WeiDU functions are in `chriz-bg-playable-races/lib/race_functions.tpa`. A mod that adds a
race ships that file and the three hook files in its own folder, for instance `mymod/lib` and
`mymod/race`, and names the folder where a function asks for it.

1. **Check that the game can take it.** Require EEex: its `M___EEex.lua`, the folder
   `EEex_scripts/extra_pattern_dbs`, and the functions the hook uses (see the component's
   `REQUIRE_PREDICATE`s in `setup-chriz-bg-playable-races.tp2`). Then check the executable:

   ```
   LAF cbpr_race_hook_pattern STR_VAR folder = ~mymod/race~ RET pattern END
   LAF cbpr_code_pattern_count STR_VAR exe = ~Baldur.exe~ pattern = EVAL ~%pattern%~
     RET count error END
   ACTION_IF (error != 0) OR (count != 1) BEGIN FAIL ~...~ END
   ```

   The pattern must occur exactly once in the executable's code sections. It does in the
   BG:EE and BG2:EE 2.7.3.0 executables (EET runs BG2:EE's); other games and versions are not
   checked, and the check stops the install there instead of hooking blind.
2. **The race number.** An entry in `RACE.IDS` (`IDS_OF_SYMBOL (~race~ ~MYRACE~)`, else
   `APPEND`), between 8 and 255 and not 153. The hook compares one byte, and 153 has the elf's
   case in the engine.
3. **The rules tables.** An entry for the label in each table above that the game has:

   ```
   LAF cbpr_race_table INT_VAR columns = 0
     STR_VAR table = ~ABRACEAD~ label = ~MYRACE~ base = ~HALFORC~ values = ~MOD_CON=1 MOD_CHR=-1~
     RET result missing END
   ```

   `columns` 0 for tables with races as rows, 1 for races as columns. Each entry not named in
   `values` comes from the `base` race, so a race can follow, say, the half-orc's classes and
   kits as other mods have set them. `result`: 0 added, 1 no such table, 2 an entry of that label
   exists already (another mod's), 3 no header line. `missing` lists names in `values` that the
   table lacks. The functions read every line themselves, so short rows, LF line ends and columns
   in any order work. This mod stops when `ABRACEAD` or `ABRACERQ` lacks a column it sets (the race
   would roll its abilities without its limits) and when a table has the label already, and warns
   for a missing entry elsewhere.
4. **The race lists of character creation.** A row for the race number in every race text table
   a campaign uses, with `NAME` (lower case, the list), `DESCSTR` (the description), `UPPERCASE`
   (the record screen) and `BIOGRAPHY`. The list keys each race by its row and stops at the
   first row without a description, so the row goes in front of that one. This mod does this
   with `hg_offer_race` in `lib/hg_functions.tpa`.
5. **Register the race with the hook.**

   ```
   LAF cbpr_register_race INT_VAR id = myrace bio = RESOLVE_STR_REF (@20)
     STR_VAR label = ~MYRACE~ folder = ~mymod/race~ RET error END
   ACTION_IF error BEGIN FAIL ~...~ END
   ```

   It adds the row to `CBPRRACE.2DA` (creating it from the folder's copy) and installs the hook's
   files. `error`: 1 a race number the hook cannot label, 2 a label that is not capital letters,
   digits and `_`, 3 the list gives the race or the label to another race already, 4 the list has
   no `ID` column. Nothing is changed then.

Install such a mod after mods that change the rules tables of the base race (for instance mods
that open all classes to all races), so that the new race copies their entries.

## The look

The engine has no character animation for a new race. Character creation gives it the human's,
and finishing a dual-class picked the animation again from class and race in the lab, the
human fighter's (run 17b). A race with a look of its own sets it again after both. This mod puts a block per party slot on top of the
campaigns' world scripts:

```
IF
  Race(Player1,HOBGOBLIN)
  !StateCheck(Player1,STATE_REALLY_DEAD)
  EEex_LuaTrigger("return CBPR_HasCharacterAnimation(0)")
THEN
  RESPONSE #100
    ApplySpellRES("HGPCRACE",Player1)
    Continue()
END
```

`CBPR_HasCharacterAnimation(slot)` is true while the party member in that slot (0 = Player1)
has a character animation (`0x5000`-`0x6FFF`), as character creation and dual-classing give.
`HGPCRACE` sets the hobgoblin's animation and colours and adds the race's spell effects (here: +1
to hit against elves, `op178`); its first effect, `op321` on itself, removes the effects of an
earlier application, so it can be applied again after each dual-class.

## What is tested

- Offline (`tests/run_tests.py`): the table functions on many layouts, the pattern search on
  synthetic PE files, the race registration and its refusals, the hobgoblin's race data, and the
  component's checks without EEex, without the trigger, without the engine code, with it twice
  and with a race number the hook cannot label.
- Lab (EET over BG2:EE 2.7.3.0, EEex v1.2.0, a copy of a modded install in which Artisan's
  Kitpack opens all classes to all races; runs 17 to 18c, 2026-10-19): the hook active at game
  start and after reloading; the hobgoblin in the race list with its description and, in EET,
  its biography; the half-orc's 21 classes and its thief kits; 3,000 ability rolls within the
  limits; the thief skills of the race's row; infravision; +1 to hit against elves; dual-class;
  saving and reloading; saves of older versions of this mod; uninstall restoring every file
  under `override` and `EEex_scripts`. Details: [hobgoblin.md](hobgoblin.md#why-it-is-built-this-way).
- Lab with EEex v1.3.1 (the same game version, a copy of a newer modded install, again with all
  classes open to all races; runs 23a to 23e, 2026-10-23): the engine code once, the hook active
  at game start and after every reload, and the same race list, classes, kits, rolls, thief
  skills, dual-class, saving and reloading and uninstall as with v1.2.0.

Not tested: BG:EE and SoD outside EET (same function bytes), IWD:EE and PST:EE, and game versions
other than 2.7.3.0. Not looked for: engine rules that go by the race number instead of the label.

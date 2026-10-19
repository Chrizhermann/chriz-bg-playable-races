# Hobgoblin protagonist (component 100)

The component builds everything from the installed game: the hobgoblin animation INI
`8100.ini`, the `MHOB*` sprite files, `HOBGOB.CRE` colours, the game's item list, the race
tables, the game's ten hobgoblin sound clips and the campaigns' world scripts. The hobgoblin is
a race of its own: the engine reads its rules from the race tables under the label
`HOBGOBLIN`, which an EEex hook gives race 111 ([new-race-with-eeex.md](new-race-with-eeex.md)).
So the component needs EEex.

## The rules

The hobgoblin of AD&D 2nd edition's *The Complete Book of Humanoids* (CBOH), with Chris's
changes (decided 2026-10-19). The installer writes them into the race tables (step 5).

| | CBOH | This mod |
|---|---|---|
| Ability adjustments | Charisma -1 | Constitution +1, Wisdom -1, Charisma -1 |
| Ability limits | Strength 6, Dexterity 6, Constitution 5 at least; Charisma 14 at most | Strength and Dexterity at least 6; Constitution 12-19; Wisdom and Charisma at most 17 |
| Thief skills | Open Locks +5%, Find Traps +5% | the human's, with Open Locks +5%, Find Traps +5%, Move Silently +10%, Hide in Shadows +5% |
| Infravision | 60 feet | yes |
| Hatred of elves | yes | +1 to hit against elves |
| Classes | the book's list | the half-orc's in the installed game, with its kits, mage schools and racial to-hit bonuses |
| Dual-class | humans only | yes |

Left out: the book's level limits (the games have none), its sense for new construction
underground (no game mechanic), and its Charisma limit of 14, which would rule out paladins
(17), bards and druids (15) where a mod opens all classes to all races. The limits are those of
the roll: the engine rolls within `ABRACERQ` and adds `ABRACEAD` afterwards (lab run 18), so
`MIN_CON` 11 and `MAX_CON` 18 with +1 give 12-19.

## What the installer builds

1. **Look codes in use.** Every item of a melee type (dagger, mace, sling, small and large
   sword, hammer, morning star, flail, axe, staff, spear, halberd, club, great and bastard
   sword) or a launcher type (bow, crossbow) contributes its two-character look code
   (`ITM 0x22`). Slings count as melee: there is no sling-throw animation, so the hobgoblin
   swings with the sling in hand.
2. **Weapon groups and bodies.** Each melee code is drawn as a weapon group: the code's
   meaning in the IESDP where it has one (`AX` axe, `CL` club, `DD` dagger, `FL` flail,
   `FS` `S1` `S2` `S3` `SC` `SS` sword, `HB` halberd, `MC` mace, `MS` morning star, `QS`
   staff, `SL` sling, `SP` spear, `WH` hammer), else the group of most of the items that use
   it, by item type (ties: sword, halberd, axe, spear, staff, mace, morning star, hammer,
   club, flail, dagger, sling). The engine names the weapon layer after the code's first
   letter, so codes of different groups with the same first letter (`SS` and `SP`, `MC` and
   `MS`, `FS` and `FL`, ...) need bodies of their own: `HGPM`, then for each further body
   the first of `HGP1`-`HGP9` that no BAM of the game starts with.
3. **Animation INIs.** The hobgoblin animation is `monster_layered`: it draws a weapon only
   when the active weapon's look code equals one of the two codes in its INI. So the
   protagonist gets one INI per pair of codes of one body, in free slots after `0x8100`
   (`HG_HOBGOBLIN_PC_<n>` in `ANIMATE.IDS`). The melee base INI holds long sword and
   halberd on `HGPM`, the launcher base INI longbow and heavy crossbow on `HGPR`. Each INI
   copies `8100.ini` with `move_scale=9`, its own body files and no selection or
   battle-cry sounds.
4. **Sprite files.** Each melee body is the hobgoblin with the two-handed attack (the bow
   shot, cycles 16-23) replaced by the one-handed slash (cycles 0-7). `HGPR*` keeps the bow
   shot for launchers. Each body gets one weapon layer per first letter in use: the group's
   art, shipped in `hobgoblin/weapons` (drawn by `tools/hob_weapon_art.py` along the game's
   sword layer `MHOBS*`), coloured with that sword layer's palette, when the game's hobgoblin
   sprites have the frame geometry the art was drawn for. The art lists two checksums per
   sprite file over its cycles, frame sizes and centres; the BG:EE, BG2:EE and EET sprites
   all match. Swords get the hobgoblin's own sword layer, and so does every group without
   art in `art.tpa` or on another geometry (another mod's hobgoblin sprite; the installer
   warns). Launchers get the hobgoblin's bow. Without `art.tpa` the mod is incompletely
   unpacked, and the installer stops before it changes anything.
5. **Race HOBGOBLIN.** Before anything changes, the component checks EEex (`M___EEex.lua`,
   the hook's functions in `EEex_scripts`, the folder `EEex_scripts/extra_pattern_dbs`,
   `EEex_LuaTrigger` in `TRIGGER.IDS`), that `RACE.IDS` gives HOBGOBLIN a number the hook can
   label (8-255, not 153), and that the code sections of `Baldur.exe` contain the hook's
   pattern exactly once. Then `hobgoblin/race.tpa` writes:
   - an entry `HOBGOBLIN` in each race table the game has; every entry not set below is the
     half-orc's (`HALFORC`), for thief skills the human's:

     | Table | Entry |
     |---|---|
     | `ABRACEAD` | `MOD_CON` 1, `MOD_WIS` -1, `MOD_CHR` -1, the others 0 |
     | `ABRACERQ` | `MIN_STR` 6, `MIN_DEX` 6, `MIN_CON` 11, `MIN_WIS` 4, `MIN_CHR` 4, `MIN_INT` 3, every maximum 18 |
     | `SKILLRAC` | the human's row, `OPEN_LOCKS` +5, `FIND_TRAPS` +5, `MOVE_SILENTLY` +10, `HIDE_IN_SHADOWS` +5 |
     | `RACEFEAT` | `VALUE` 1 (infravision) |
     | `CLSRCREQ` | the half-orc's column, `DUALCLASS` 1 |
     | `KITTABLE` | the half-orc's column (`K_<class>_HO`) |
     | `MGSRCREQ`, `RACETHAC` | the half-orc's column |
     | `RACECOLR` | `SKIN` and `HAIR`: the hobgoblin's colours from `HOBGOB.CRE` |

     A table with a `HOBGOBLIN` entry of another mod stops the install, and so does an
     `ABRACEAD` or `ABRACERQ` without a column the race sets (it would roll without its
     limits); any other missing entry only warns. The tables are read line by line, so short
     rows, LF line ends, columns in any order and other mods' rows and columns work.
   - a row `HOBGOBLIN` for race 111 in every race table a campaign uses (column `RACETEXT` of
     `CAMPAIGN.2DA`, EET: `RACETEXT`, `BGRACTXT`, `SODRACE`; and `RACETEXT.2DA` itself), in
     front of the first row without a description: the race list keys each race by its row and
     stops at a gap. The row has the names `hobgoblin` and `Hobgoblin`, the description, and
     the hobgoblin's biography in each table where the human has one. A table with a row for
     race 111 or `HOBGOBLIN` already stops the install. Whatever the column names say, the
     games keep the lower-case name the race list shows in `NAME` ("half-orc") and the
     capitalized one the record screen shows in `UPPERCASE` ("Half-Orc"), and the record
     screen finds a race's row by its ID.
   - the race in the hook's list `CBPRRACE.2DA` (label, number, biography), and the hook's
     files: `M_CBPRRC.lua` in `override`, `CBPRRACE.db` in `EEex_scripts/extra_pattern_dbs`.
     At game start the hook makes `CRuleTables::GetRaceString` answer race 111 with
     `HOBGOBLIN`, and adds race 111 to EET's `bioRaceData`, from which character creation
     takes the biography's race part.
6. **Marker state.** `HG_HOBGOBLIN_PC` in `SPLSTATE.IDS` (existing entry, else the first
   free state). `SPLPROT.2DA` rows for "state not set" `(0x112, -1, 5)` and "state set"
   `(0x112, -1, 1)` are reused when present, else appended.
7. **Weapon switches.** Every melee weapon, launcher and sling gets two equipped effects:
   `op318` makes every creature without the marker immune to the switch, then `op177`
   applies an EFF with `op53` to the INI for the weapon's code (else its body's base INI).
   Ammunition and darts stay untouched, because the engine treats quiver items as always
   equipped. When a save loads, the engine equips the items before the saved effects are in
   force, so each `op318` would shield the marked hobgoblin too. So the installer also copies
   `hobgoblin/M_CBPRHG.lua` into `override`: at game start EEex registers it as a listener
   that runs for each creature as it loads, after its saved effects are read and before its
   items are equipped. A creature whose saved effects set the marker (`op328`, special not 0,
   the state in parameter 2, not delayed) gets the marker state there; nothing is saved, and
   every other creature stays as it is. `CBPR_HobgoblinLook.Status` and the console tell
   whether it is active.
8. **Armour colours.** Body armour with look code `2A` (leather), `3A` (chain), `4A`
   (plate, full plate) or `2W`/`3W`/`4W` (robes) gets an equipped `op272` that attaches
   `HGA<code>.EFF` to the wearer once per second. That EFF's `op326` applies
   `HGA<code>.SPL` only to a creature with the marker state. The spell sets the metal and
   armor colour ranges, and for robes the cloak, for 3 seconds.
9. **Race spells.** `HGPCRACE` gives a hobgoblin the hobgoblin's look and the race's spell
   effects. First `op321` removes its own earlier effects and those of the transformation of
   v0.1 and v0.2 (`HGPCXFRM`, `HGPCXNOW`): v0.2's thief skill and infravision effects would
   now count on top of the race tables. Then: the permanent base animation (melee base INI),
   the base colours for skin, hair, leather and minor ranges from `HOBGOB.CRE`, the marker
   state, and `op178` with timing 9 (parameter 1 the `ELF` entry of `RACE.IDS`, parameter 2 4
   for `RACE.IDS`, special 1 the bonus): +1 to hit against elves. `HGPCXFRM`, the innate
   ability "Become a Hobgoblin" of v0.1 and v0.2 (with the icons of the installed Polymorph
   Self, `SPWI416`, when present), stays for saves whose protagonist still has it: race
   HOBGOBLIN and `HGPCRACE`'s effects, then it removes itself (`op172`). No one gets it
   anymore.
10. **World scripts.** On top of every world script that `CAMPAIGN.2DA` names (EET: `BALDUR`,
    `BALDUR25`, `BDBALDUR`; `BALDUR.BCS` when the table names none), `race_look.baf` adds:
    - one block per party slot: a member of race HOBGOBLIN, not dead, with a character
      animation (`CBPR_HasCharacterAnimation`, Lua through `EEex_LuaTrigger`; `0x5000`-
      `0x6FFF`) gets `HGPCRACE`. Character creation gives the race the human's figure, and in
      lab run 17b finishing a dual-class picked the figure again from class and race (the human
      fighter's);
    - once per game (global `CBPR_HOBGOBLIN_RACE`), a protagonist of race HOBGOBLIN with the
      marker gets `HGPCRACE`: a hobgoblin of v0.1 or v0.2 loses that version's effects and
      gains the hatred of elves. A hobgoblin of this version matches once too; `HGPCRACE` then
      only replaces its own effects.
11. **Inventory figure.** `<body>INV.BAM` for each body (`HGPMINV`, `HGP1INV`, ...) and
    `HGPRINV.BAM`, from `MHOBG1.BAM`: frame 0 of
    cycle 16 (standing, facing south) at twice the size, with the source palette, as a
    two-frame BAM (figure and a 1x1 blank) with one cycle `0, 0, 1`. The centre `-4, -16`
    is where the lab prototype sat right on the paperdoll. The blank pixel is the palette's
    transparent colour (the first `RGB(0,255,0)` entry, else entry 0, as the engine picks
    it) and the header keeps the source's RLE index, so a hobgoblin sprite from another
    mod that uses other indices for them still gives a clean figure.
12. **Voice set `CBPRHG`.** All ten hobgoblin clips of the game (`HOBGL01`-`HOBGL10`), each
    on the event it fits, registered with the EE Soundset Tool's `cd_add_soundset`
    (`lib/cd_add_soundset.tph`, shipped unchanged):

    | Event | Slot | Clip | What it is |
    | --- | --- | --- | --- |
    | Selected | common 1 | `HOBGL01` | "You be quiet!" |
    | Selected | common 2 | `HOBGL02` | "Manure mouth." |
    | Order (moving, acting) | action 1 | `HOBGL03` | "Forward march!" |
    | Order (moving, acting) | action 2 | `HOBGL06` | low growl |
    | Battle cry (attacking) | battle cry 1 | `HOBGL04` | "Spare no one!" |
    | Battle cry (attacking) | battle cry 2 | `HOBGL10` | attack yell |
    | Hit | damage 1 | `HOBGL08` | grunt |
    | Death | dying 1 | `HOBGL09` | high wail |
    | Badly wounded | hurt 1 | `HOBGL07` | short high yelp |
    | A party member dies | death of a party member 1 | `HOBGL05` | "Noo!" |
    | Becomes leader | leader 1 | `HOBGL03` | "Forward march!" again |
    | Critical hit | critical hit | `HOBGL04` | "Spare no one!" again |

    - Orders and battle cries are what a player triggers most, so each has two clips: moving and
      attacking always have a line to play. Selection has the hobgoblins' own
      two selection lines.
    - Only two clips serve a second slot, and both on rare events, so the voice does not
      keep repeating itself. Everything else (area comments, bored, tired, ...) stays
      empty, as in the deliberately sparse voice packs.
    - Each slot gets its own copy of its clip under the tool's file name for that slot
      (`CBPRHG` plus `f`, `g`, `i`, `j`, `a`, `8`, `l`, `m`, `e`, `w`, `b`, `z`), all in
      `lang/<language>/sounds`. Its line is the game's own subtitle for the clip: the text of
      the lowest string that plays it, without a leading tag such as `[HOBGOBLIN 01]`, so
      the subtitles follow the game's language. Clips without text stay without subtitle.
    - `cd_add_soundset` puts the strings into a `CHARSND.2DA` column in the game's row
      order (BG:EE and BG2:EE/EET order some rows differently) and adds the menu name
      "Hobgoblin" to `M_cdsnd.lua`, next to other voice packs' lines.

    Without a voice set, and with a warning, nothing copied and nothing changed: when
    `CHARSND.2DA` lacks the 99 rows 1-99, when the name is taken already (a `CBPRHG`
    column, a `CBPRHG` menu name in `M_cdsnd.lua`, or one of the sound files), or when no
    clip fills a one-character slot. A name counts as taken only on a line that sets
    `filenames_stringrefs['CBPRHG']` (either quote). A clip the game lacks leaves its slot
    empty, with a warning.

## Why it is built this way

Findings from the lab (EET on BG2:EE 2.7.3.0; EEex, then for inspection only), 2026-10-17:

- `op318` blocks an `op177` EFF only when the EFF names itself as parent resource (EFF V2
  `0x90` type 1, `0x94` own name). WeiDU's `CREATE ~EFF~` leaves both empty, so the
  installer writes them.
- `op328` must use `special = 1` for a `SPLSTATE.IDS` state, else the state never reads
  as set.
- An `op7` colour change through `op177` never shows. `op272` attaches the EFF to the
  creature instead, and those colours show.
- `op318` does not stop an `op272` attachment: a companion in patched armour took the
  colours. The `op326` check inside the EFF fixed this; the companion then stayed
  unchanged although the `op272` ran on it.
- A timed `op7` wins over the armour's own colour effects.
- Every weapon carries its own switch. Without one, replacing the selected weapon could
  keep the previous weapon's sprite until the next weapon change.
- Armour worn in a save made before the install had the new `op272` right after loading.
- The voice menu lists the voices whose files lie in `lang/<language>/sounds` (42 file
  prefixes there gave the 43 entries of the list); a `CHARSND.2DA` column and the
  `M_cdsnd.lua` name alone do not show up. Hence the name limit: six characters plus a
  file character or two make the eight a resource name may have. With the files there
  (lab run 11), "Hobgoblin" appears in Record > Customize > Voice. Choosing it gives the
  protagonist the voice set's strings in slots 1-34, also after saving and loading.
- `move_scale` 9 walked about 8 % slower on this body than a human character animation at
  the same value (96.5 against 105.3 pixels per second). The vanilla `8100.ini` uses 5.
- Uninstall (lab run 12, 2026-10-18, with the test package): the install changed 1,560
  override files and added 146 (140 in `override`, 6 sounds in `lang/en_US/sounds`).
  After the uninstall, all 165,141 files of the game folder matched the state before the
  install, except WeiDU's `.DEBUG` log. A fresh install appends ten strings to
  `dialog.tlk` (the race description, `HOBGOBLIN`, the ability's name and description,
  six voice lines); they stay after an uninstall, unused. A save made after the
  transformation still loads without the component, and the inventory and record screens
  open. The protagonist keeps animation `0x8101`, which the game then draws as the plain
  hobgoblin with the vanilla `move_scale` 5. The inventory figure is empty, the race has
  no name, and the voice slots point to strings whose sound files are gone.

The voice, 2026-10-18:

- v0.1 copied the hobgoblin creatures' own sound table slot for slot. Chris's live test
  found it unusable ("klappt überhaupt nicht"): the creatures fill only six slots (two
  battle cries, two selection lines, hit, death), so orders and moving stayed silent and
  the lines played at events they were not written for. Rows and file names had matched
  the EE Soundset Tool; what was missing was choosing a line per event, as the curated
  packs in `chriz-bg-voicepacks` do.
- Which slots a player character uses comes from the tool's authors
  ([CamDawg's and MJK's posts in the tool's thread](https://www.gibberlings3.net/forums/topic/34560-adding-soundsets-to-the-ees-using-the-ee-soundset-tool/)):
  action acknowledgements play when a character is given an order such as moving,
  battle cries when it starts a fight, selection lines when it is selected. Attack sounds
  are ignored in favour of the weapon's sound; happy, unhappy and breaking point are
  reactions of NPCs to the party's reputation; common selection 7 never plays; damage 2
  and 3 make the damage line play only part of the time. The voice uses none of those.
- `HOBGL01`-`HOBGL04` have subtitles. The other six do not (or only "Noo!" and "Rrr!"), so
  they were told apart by length, loudness, pitch and a local Whisper transcription:
  `HOBGL05` is a drawn-out "Noo!", `HOBGL06` a low growl, `HOBGL07` a short high yelp,
  `HOBGL08` a grunt, `HOBGL09` a high wail, `HOBGL10` a yell. In the game, `HOBGL08` and
  `HOBGL09` are the creatures' hit and death sounds, and the hobgoblin animation INI uses
  `HOBGL06` for its melee swings and `HOBGL10` for its attack (each listed with two
  `blank` entries).
- The protagonist's animation INIs keep those attack, hit and death sounds, as on the
  game's hobgoblins, whatever voice the protagonist has.
- Lab check of the test package on EET 2.7.3.0 (runs 13 and 13b). The lab runs without
  sound, so the message log's subtitles and the engine's state stood in for listening.
  - The installer added the twelve sound files, the `CHARSND.2DA` column, the strings and
    the menu line, without a warning. **Hobgoblin** was listed under Customize > Voice, and
    choosing it filled exactly the twelve slots of the table, rows 53 and 65 included.
    Slot 74 holds the protagonist's biography (`BIO` in `SOUNDOFF.IDS`).
  - Each line with a subtitle showed it when played; the clips without text showed none.
  - Six selections of the protagonist played the two selection lines in turn.
  - Moving: the engine's function for a click on the ground
    (`CGameArea::OnActionButtonClickGround`, which EEex's keybinds use for orders) moved
    the protagonist nine times, and each move played an order line ("Forward march!" or
    "Rrr!"). One click on a spot it could not walk to moved it nowhere and played nothing.
  - Attacking: four attack orders on a hobgoblin captain through the engine's click
    function for objects (`virtual_OnActionButton`) each started an attack. With four more
    attacks the party AI started, "Spare no one!" came twice in eight attack starts; the
    other battle cry has no subtitle. The engine does not play a battle cry at every
    attack start: in the same fight Keldorn and Yoshimo, with three subtitled battle cries
    each, gave none in four and two attack starts, Sir Anomen one at each of his four.
  - Clicks sent to the world screen's mouse handlers
    (`m_pEngineWorld:virtual_OnLButtonDown/Up`) gave no order at all.
- Updating from v0.1: a character keeps the lines its voice had when the voice was
  chosen. The lab save's protagonist still had v0.1's six lines after v0.1 was uninstalled
  and v0.1.1 installed, until **Hobgoblin** was chosen again. WeiDU leaves added strings in
  `dialog.tlk`, so those lines stay valid and now name the new sound files, under v0.1's
  subtitles.

Character creation and the race in v0.2, 2026-10-17 and 2026-10-18 (lab runs 14-16). v0.2
created the hobgoblin as a template race and transformed it; v0.3 replaced that with a race of
its own (next section). The engine facts below hold without the hook:

- A race 111 row with a description in each campaign race table puts the hobgoblin into the
  race list (run 14). The list keys each race by its row and stops at the first row
  without a description, so the row goes in front of that one.
- Choosing race 111 itself offers no class (run 14b): the engine labels only its seven races,
  and a race without a label gets the race tables' defaults. Hence v0.2's routed choice, which
  created the template race.
- `C:SetGlobal` works in character creation with cheats off. In run 15 the hobgoblin
  choice set `CBPR_HOBGOBLIN_CHARGEN` to 1, the other races to 2, and the world script made
  the protagonist a hobgoblin as the game began: race 111, animation `0x8101`, the marker,
  no ability left.
- EET takes the biography's race part from `bioRaceData`; with the hobgoblin's entry,
  character creation showed the hobgoblin biography (run 15).
- The engine gives race 111 nothing from `SKILLRAC.2DA` or `RACEFEAT.2DA`. Baldur.exe names
  the rows of its seven races itself: `HUMAN`, `DWARF`, `GNOME`, `ELF`, `HALF_ELF`,
  `HALFLING`, `HALFORC` lie in its data next to the skill column names. A thief with the
  same spent points (6/6/6/6/6/5/5) had 21/16/16/16/11/10/5 as a half-orc and
  21/16/11/16/11/15/5 as a human, but only its points as a goblin (161) or a hobgoblin
  (111), although `SKILLRAC.2DA` had a `HOBGOBLIN` row (runs 15, 15c). Racial infravision
  (`m_bInfravisionOn`) was on for a half-orc and a dwarf, off for a goblin and a hobgoblin,
  although `RACEFEAT.2DA` had rows for both (run 15d).
- The engine adds the race row only for the classes and kits that have the skill. Across
  all 21 classes, comparing a dwarf with a goblin (run 15d): thieves and every multi-class
  thief got all seven skills, bards pick pockets, rangers and cleric/rangers find traps,
  move silently, hide, detect illusion and set traps (this lab has Artisan's Kitpack's
  ranger overhaul), monks find traps, move silently and hide, shamans detect illusion,
  every other class nothing. That is the pattern of `THIEFSCL.2DA`.
- Effects count by the same rule. An `op90` with timing 9 counted for the thief and not for
  the same character as a fighter, while an `op92` with timing 1 went into the base skills
  and counted for both (run 15c). Hence the race row as effects with timing 9. In run 16 the
  hobgoblin's effects gave exactly the engine's share of the half-orc row for thief,
  fighter, bard, ranger, monk and shaman. A Blade, whose kit gets half of the bard's pick
  pockets, had 13 both as a hobgoblin with the effects and as a half-orc without them
  (6 + 15 / 2, rounded down; runs 16, 16b): the engine adds the bonuses up before it
  halves them.
- The level-up screen shows the skills with these effects (run 15c).
- After the transformation the thief had the skills of its character creation: component
  100 21/16/16/16/11/10/5 (run 16), component 101 21/16/11/16/11/15/5 (runs 16b, 16c). All
  had `m_bInfravisionOn` 1, and every uninstall restored every patched file.
- The record screen shows the race table's `UPPERCASE` string for the race, found by its ID:
  "Half-Orc", "Human", "Goblin" (run 15c). The first v0.2 install had the two names the
  other way round, so the record screen showed "HOBGOBLIN" and the race list "Hobgoblin"
  among "human" to "half-orc". Now they show "Hobgoblin" and "hobgoblin" (runs 16, 16b).
- The record screen offers dual-classing by the race's `DUALCLASS` entry in `CLSRCREQ.2DA`
  (in the games: humans only). With every ability at 18 and the level-up to thief level 2
  done, its dual-class button was on for the character as a human, off as a hobgoblin without
  the hook and on again as a human (component 101, run 16c). A pending
  level-up, and level 1, keep the button off for every race (runs 15d, 16b).

The race of its own, 2026-10-19 (lab runs 17 to 19, EET over BG2:EE 2.7.3.0 with EEex
v1.2.0, the lab copy of Chris's install, where Artisan's Kitpack opens all classes to all
races):

- Runs 17 and 17b proved the hook with marker values for race 111 in seven race tables
  (classes and dual-class, kits, ability adjustments and limits, thief skills, infravision,
  colours; not `RACETHAC` and `MGSRCREQ`); [new-race-with-eeex.md](new-race-with-eeex.md)
  describes the method.
- v0.3.0 as installed (run 18): no warning. At the start screen `CBPR_RaceHook.Status` was
  "active for HOBGOBLIN (111) at 0x140246440", and `bioRaceData` had race 111's entry with the
  hobgoblin's biography.
- Character creation listed "hobgoblin" eighth, with its description. It offered the same 21
  classes as to the half-orc and, for a thief, the same nine kits. 3,000 rerolls each for a
  thief: hobgoblin STR 6-18, DEX 9-18 (the thief's minimum), CON 12-19, INT 4-18, WIS 3-17, CHA
  3-17; half-orc STR 5-19, CON 4-19, INT 1-16; human STR 4-18, CON 3-18. The engine rolls within
  `ABRACERQ` and adds `ABRACEAD` afterwards, without limiting the sum again (the half-orc's
  INT 1).
- Thief skills at DEX 13-15 before any points (pick pockets to set traps): hobgoblin
  15/15/10/20/10/10/0, human 15/10/5/10/5/10/0, half-orc 15/10/10/10/5/5/0; in this install the
  `SKILLRAC` rows hold the whole base. In the game, with 6/6/6/6/6/5/5 points:
  21/21/16/26/16/15/5.
- In the world, when the driver first looked: race 111, the hobgoblin figure (`0x8101`, with
  the staff `0x8108`), the marker, `op178` against `ELF` (special 1), racial infravision, and
  the race "Hobgoblin" on the record screen. The once-per-game block for older saves had
  matched this new hobgoblin too; `HGPCRACE`'s effects were there once each.
- Dual-class: at thief level 2 (abilities set to 18) the dual-class button was on, and fighter,
  cleric and mage were offered. After dual-classing to fighter: Fighter/Thief with fighter level
  1 and thief level 2, race 111, and the hobgoblin figure two seconds later.
- Saving and reloading kept race, figure, marker and effects; the hook was active after the
  reload.
- A v0.1 save (a paladin made a hobgoblin with the ability, run 11): after loading, the block
  for older saves had given `HGPCRACE` (race 111, figure, marker, `op178`). A v0.2 save (a thief
  of the run 16 series, made a hobgoblin by v0.2's transformation): of the `HGPC*` effects only
  `HGPCRACE`'s were left, so v0.2's skill effects were gone, and the thief had
  21/21/16/26/16/15/5, the hobgoblin row plus its points.
- Infravision (runs 18b, 18c): `CGameSprite::AIUpdate` sets the sprite's `m_bInfravisionOn` for
  a party member that is not asleep when its state has `STATE_INFRAVISION` (`op63`) or
  `CRuleTables::GetRaceFeatures` finds infravision for its race (`RACEFEAT.2DA`, under the
  race's label), and clears it otherwise. In run 18c it was set only while that member was the
  only one selected. The v0.1 protagonist had it with its infravision helmet and still after the
  helmet was destroyed: the race gives it, also to hobgoblins made in older versions.
- The weapon look after loading (run 18b): a save made with the staff selected loaded with the
  melee base INI (`0x8101`). At load the staff's `op318` (immune unless the marker is set) was
  in its equipped effects and its `op177` was not. Selecting the fist and the staff again gave
  `0x8108`. The switches date from v0.1; earlier lab saves had fists selected. The cause, in
  the engine code of 2.7.3.0: `CGameSprite::Unmarshal` computes the creature's stats from its
  base values and reads its saved effects into the timed effect list without applying them;
  then `CGameSpriteEquipment::Unmarshal` equips each item and applies its equipped effects at
  once, against those stats, which lack the marker. `op318` checks its `SPLPROT.2DA` row each
  time it is applied and is dropped only when the check fails, while `op177` checks for an
  immunity only on its first application. So the `op318` stayed, and every later recalculation
  applies the equipped effects before the timed ones (the marker's `op328`). Selecting a weapon
  equips it again against the full stats, which is why that helped.
- The fix (run 19, 2026-10-19): EEex's `EEex_Sprite_AddLoadedListener` runs inside
  `CGameSprite::Unmarshal` after the timed effect list is read and before the items are
  equipped (EEex v1.2.0 in the lab; the same hook in v1.3.1's code). `M_CBPRHG.lua` sets the
  marker state there for a creature whose saved effects carry the marker. Saves made with a
  staff, an axe and a bow selected loaded with `0x8108`, `0x8103` and `0x8102`, right away and
  5 seconds later, with the `op177` in force and the `op318` gone; so did the run 18b save.
  With the listener switched off in the lab, the axe save showed the old bug again (`0x8101`).
  An enemy vanilla hobgoblin (`HOBGOB`, EA 255) given an axe kept `0x8100` before saving and
  after each load (`op318` kept, no `op177`). The five companions of the run 11 save kept their
  animations; four held weapons with a switch (hammer, two-handed sword, two bows), whose
  `op318` stayed, with no `op177`. The console reported the listener active for spell state 195.
- Uninstall (runs 18, 18b, 18c, 19): all 40,866 files under `override` and `EEex_scripts`
  matched the state before the install.

The weapon art, 2026-10-18:

- In run 15 every weapon switched to its INI, but staves, spears and halberds showed as
  dotted lines: the tool set 41 points along every shaft, so a shaft longer than 40 pixels
  had gaps. With a point every half pixel the shafts are whole (run 16). Run 16d showed all
  19 test weapons with the final art, each on its group's INI.
- Some frames of the game's own sword layer are empty (`MHOBG1E` cycles 8-12, 16-20,
  24-28), and the art leaves those frames empty for every group as well. In run 16d the
  sword and the drawn weapons alike were not to be seen while the arm was raised for the
  blow. In every frame of the four sprite files where the sword
  shows, every group's layer has pixels (checked on the EET sprites).
- The art ships with the mod (decided 2026-10-19). From the game the tool takes only where
  the hand is and where the body covers it, frame by frame; the pixels are its own drawing
  in its own few colour indices, and the files carry no palette.

## Tests

`python tests/run_tests.py --weidu <weidu.exe>` runs the library's functions in small
synthetic game folders (made-up tables, strings, creatures, scripts and sprites; no game
needed):
- world-script discovery, and the shipped `race_look.baf` compiled on top of the world
  scripts;
- the `CHARSND.2DA` check and the clips' subtitles from the string table;
- the curated voice in BG2:EE, EET and BG:EE row order: strings, sound files, menu line
  next to other voice packs' lines, uninstall, and the cases where no voice set may be
  made;
- the shipped `cd_add_soundset.tph` byte for byte, and the hobgoblin voice's table: all ten
  clips, at most two used twice, orders, battle cries and selection filled, no slot that
  is silent for player characters;
- the inventory figure, also from sprites with other transparent and RLE indices;
- weapon groups and bodies from a game's items (IESDP codes, the majority by item type and
  its tie order, codes in any letter case, slings), and the free body names;
- the frame-geometry checksums (the same as `tools/hob_weapon_art.py` computes), and the
  weapon art copied with the game's palette;
- the shipped weapon art: one file per group and sprite file, no palette, no colour but the
  tool's own, the same cycles in every group, and the checksums of all eight sprite files;
- the race in character creation: the row in a race table (placement behind the described
  rows, columns in any order, a taken label or race), the race in every campaign table with
  its biography where the human has one, and the table lookup it uses;
- the race tables line by line: a race's row or column on the layouts mods leave (columns in
  another order and among others, short and long rows, blank lines, LF line ends, no final line
  end, a header only), each entry from the values given, the base race or the table's default
  value, and a taken label; single entries by row and column;
- the hobgoblin's race data (`race.tpa`) on plain and modded tables, with optional tables
  missing and with EET's campaign tables, and where it stops (an ability table without a column
  it sets, another mod's `HOBGOBLIN` entry, a race list with race 111) or warns (no `DUALCLASS`
  row);
- the pattern search in synthetic 64-bit PE files: once, twice, none, a near miss, wildcards
  filled with `%`, `~` and 0, data and non-executable sections, a match at a section's end, a
  pattern with `%` and `~` among its fixed bytes, no file, no PE file, bad patterns;
- the hook's race list: a new list, a second race, the same race again, a label or number
  another race has, numbers and labels the hook cannot take, no `ID` column, the hook's files
  from another mod's folder, uninstall; and that the hook's Lua, pattern file, installer and
  world script agree;
- that the load listener and the installer agree: the same `SPLSTATE.IDS` name for the marker,
  the race spell's `op328` as the listener counts it, and the copy into `override`;
- the component's checks with the real tp2: no EEex, no script trigger, no hook functions, no
  executable, the engine code missing or twice, race number 153; each stops before any game
  file changes;
- weapon shafts without gaps at any length and angle, and each weapon with connected parts
  drawn in one piece;
- world scripts from a `CAMPAIGN.2DA` without data rows, as BG:EE and BG2:EE 2.7 have;
- a WeiDU parse check of the tp2, every tpa and the tph, and the language file against
  every `@N` the sources use and against what WeiDU writes into `dialog.tlk`.

The tests include uninstall. Any WeiDU 249 or newer works, also a mod's `setup-*.exe`.

## Open

- EEex v1.3.1, BG:EE and SoD outside EET, and game versions other than 2.7.3.0: not
  lab-tested.
- Listening to the voice in a real game: the lab runs muted, so it checked subtitles and
  the engine's state, not the sound.
- More voice lines.
- Before a release: check the `HG*` resource names (`HGPM*`, `HGP1*`-`HGP9*`, `HGPR*`,
  `HGE*`, `HGA*`, `HGPC*`), `CBPRRACE.2DA`, `CBPRRACE.db`, `M_CBPRRC.lua`, `M_CBPRHG.lua`, the
  label `CBPR-CRuleTables::GetRaceString`, the Lua names `CBPR_RaceHook`,
  `CBPR_HasCharacterAnimation`, `CBPR_GetRaceString_Original` and `CBPR_HobgoblinLook`, the
  global `CBPR_HOBGOBLIN_RACE` and the voice set name `CBPRHG` against other mods.

# Hobgoblin protagonist (components 100 and 101)

The component builds everything from the installed game: the hobgoblin animation INI
`8100.ini`, the `MHOB*` sprite files, `HOBGOB.CRE` colours, the game's item list, the
campaigns' race tables, `UI.MENU`, the game's ten hobgoblin sound clips and the campaigns'
world scripts. The two subcomponents differ only in the template race whose rules character
creation uses for the hobgoblin: 100 the half-orc, 101 the human.

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
5. **Race in character creation.** A row `HOBGOBLIN` for race 111 in every race table a
   campaign uses (column `RACETEXT` of `CAMPAIGN.2DA`, EET: `RACETEXT`, `BGRACTXT`,
   `SODRACE`; and `RACETEXT.2DA` itself), in front of the first row without a description:
   the race list keys each race by its row and stops at a gap. The row has the names
   `hobgoblin` and `Hobgoblin`, the subcomponent's description, and the hobgoblin's
   biography in each table where the template race has one. Whatever the column names say,
   the games keep the lower-case name the race list shows in `NAME` ("half-orc") and the
   capitalized one the record screen shows in `UPPERCASE` ("Half-Orc"), and the record
   screen finds a race's row by its ID.
   - `UI.MENU`'s race selection (`createCharScreen:OnRaceSelectButtonClick`) goes through
     `cbprRaceSelect`, added to its end: race 111 creates the template race and sets the
     global `CBPR_HOBGOBLIN_CHARGEN` to 1, any other race sets it to 2.
   - Where the UI takes the biography's race part from `bioRaceData` by the race the list
     offers (EET does), choosing the hobgoblin adds race 111 there: the template's entry,
     its biographies replaced by the hobgoblin's.
   - Without a race selection to route (a UI mod that replaced `UI.MENU`), the rows get no
     description, so the list leaves the hobgoblin out, and protagonists get the ability
     instead (warned). The same when every race table has a race 111 row already.
   - After the transformation the race is HOBGOBLIN, and the engine gives race 111 nothing
     from `SKILLRAC.2DA` (thief skills) or `RACEFEAT.2DA` (infravision): it reads them only
     under the names of its seven races. So the installer reads the template race's thief
     skill row (`HALFORC` or `HUMAN`, columns by name) for the transformation (step 9) and
     adds no rows to those tables.
6. **Marker state.** `HG_HOBGOBLIN_PC` in `SPLSTATE.IDS` (existing entry, else the first
   free state). `SPLPROT.2DA` rows for "state not set" `(0x112, -1, 5)` and "state set"
   `(0x112, -1, 1)` are reused when present, else appended.
7. **Weapon switches.** Every melee weapon, launcher and sling gets two equipped effects:
   `op318` makes every creature without the marker immune to the switch, then `op177`
   applies an EFF with `op53` to the INI for the weapon's code (else its body's base INI).
   Ammunition and darts stay untouched, because the engine treats quiver items as always
   equipped.
8. **Armour colours.** Body armour with look code `2A` (leather), `3A` (chain), `4A`
   (plate, full plate) or `2W`/`3W`/`4W` (robes) gets an equipped `op272` that attaches
   `HGA<code>.EFF` to the wearer once per second. That EFF's `op326` applies
   `HGA<code>.SPL` only to a creature with the marker state. The spell sets the metal and
   armor colour ranges, and for robes the cloak, for 3 seconds.
9. **Transformation.** `HGPCXFRM`, the innate ability "Become a Hobgoblin" (with the
   icons of the installed Polymorph Self, `SPWI416`, when present, and a description that
   names the template race's traits it gives), and `HGPCXNOW`, the
   same effects for the world scripts, set the permanent base animation (melee base INI),
   the base colours for skin, hair, leather and minor ranges from `HOBGOB.CRE`, race
   HOBGOBLIN and the marker state, then remove the ability (`op172`). They also give the
   template race's thief skill row as permanent effects (timing 9: `op92` pick pockets,
   `op90` open locks, `op91` find traps, `op59` move silently, `op275` hide in shadows,
   `op276` detect illusion, `op277` set traps; values of 0 left out) and infravision
   (`op63`). The engine counts skill effects only for the classes and kits that have the
   skill, as it counts the race row, so a hobgoblin has the template race's skills in
   every class.
10. **World scripts.** Two blocks on top of every world script that `CAMPAIGN.2DA` names
    (EET: `BALDUR`, `BALDUR25`, `BDBALDUR`; `BALDUR.BCS` when the table names none) act
    once per game (global `CBPR_HOBGOBLIN_GIVEN`), when the protagonist is in the party,
    alive and not yet a hobgoblin:
    - created as the hobgoblin in this game's character creation
      (`CBPR_HOBGOBLIN_CHARGEN` 1): `HGPCXNOW`, the protagonist becomes a hobgoblin at once;
    - not created in this game's character creation (0: imported, saves made before this
      install, a UI without the routed choice): `HGPCGIVE` (`op171`) hands over the ability;
    - created with another race (2): nothing.
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

Findings from the lab (EET on BG2:EE 2.7.3.0, EEex for inspection only), 2026-10-17:

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

Character creation and the race, 2026-10-17 and 2026-10-18 (lab runs 14-16):

- A race 111 row with a description in each campaign race table puts the hobgoblin into the
  race list (run 14). The list keys each race by its row and stops at the first row
  without a description, so the row goes in front of that one.
- Choosing race 111 itself offers no class: the engine creates only its seven races (run
  14b). Hence the routed choice, which creates the template race.
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
- The record screen offers dual-classing only to humans. With every ability at 18 and the
  level-up to thief level 2 done, its dual-class button was on for the character as a
  human, off as a hobgoblin and on again as a human (component 101, run 16c). A pending
  level-up, and level 1, keep the button off for every race (runs 15d, 16b).

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
- world-script discovery, and the shipped `give_ability.baf` compiled on top of the world
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
  rows, columns in any order, a taken label or race), the routed race selection in
  `UI.MENU` (from a BIFF or override, a second call, the dry run, the biography entry),
  the race in every campaign table with and without a routable `UI.MENU`, and the table
  lookup it uses;
- the template race's thief skill row as the engine reads it: its own row names, the label
  in any letter case, columns in any order and among others, values below 0, the table's
  default value for a missing row or column, no table, and nothing for a race outside the
  seven even with a row of its name;
- weapon shafts without gaps at any length and angle, and each weapon with connected parts
  drawn in one piece;
- world scripts from a `CAMPAIGN.2DA` without data rows, as BG:EE and BG2:EE 2.7 have;
- a WeiDU parse check of the tp2, every tpa and the tph, and the language file against
  every `@N` the sources use and against what WeiDU writes into `dialog.tlk`.

The tests include uninstall. Any WeiDU 249 or newer works, also a mod's `setup-*.exe`.

## Open

- Listening to the voice in a real game: the lab runs muted, so it checked subtitles and
  the engine's state, not the sound.
- More voice lines.
- Before a release: check the `HG*` resource names (`HGPM*`, `HGP1*`-`HGP9*`, `HGPR*`,
  `HGE*`, `HGA*`, `HGPC*`), the Lua names `cbprRaceSelect` and `cbprRaceBio`, the globals
  `CBPR_HOBGOBLIN_*` and the voice set name `CBPRHG` against other mods.

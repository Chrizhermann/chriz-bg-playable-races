# Hobgoblin protagonist (component 100)

The component builds everything from the installed game: the hobgoblin animation INI
`8100.ini`, the `MHOB*` sprite files, `HOBGOB.CRE` colours, the game's item list, the
game's ten hobgoblin sound clips and the campaigns' world scripts.

## What the installer builds

1. **Look codes in use.** Every item of a melee type (dagger, mace, small and large sword,
   hammer, morning star, flail, axe, staff, spear, halberd, club, great and bastard sword)
   or a launcher type (bow, crossbow) contributes its two-character look code (`ITM 0x22`).
2. **Animation INIs.** The hobgoblin animation is `monster_layered`: it draws a weapon only
   when the active weapon's look code equals one of the two codes in its INI. So the
   protagonist gets one INI per pair of codes, in free slots after `0x8100`
   (`HG_HOBGOBLIN_PC_<n>` in `ANIMATE.IDS`). The melee base INI holds long sword and
   halberd, the launcher base INI longbow and heavy crossbow. Each INI copies `8100.ini`
   with `move_scale=9`, its own body files and no selection or battle-cry sounds.
3. **Sprite files.** `HGPM*` is the hobgoblin body with the two-handed attack (the bow
   shot, cycles 16-23) replaced by the one-handed slash (cycles 0-7). `HGPR*` keeps the
   bow shot for launchers. Weapon layers reuse the hobgoblin's sword for every melee code
   letter and its bow for every launcher letter.
4. **Race text.** A `HOBGOBLIN` row in `RACETEXT.2DA` and `RACEFEAT.2DA`, unless present.
5. **Marker state.** `HG_HOBGOBLIN_PC` in `SPLSTATE.IDS` (existing entry, else the first
   free state). `SPLPROT.2DA` rows for "state not set" `(0x112, -1, 5)` and "state set"
   `(0x112, -1, 1)` are reused when present, else appended.
6. **Weapon switches.** Every melee weapon, launcher and sling gets two equipped effects:
   `op318` makes every creature without the marker immune to the switch, then `op177`
   applies an EFF with `op53` to the INI for the weapon's code (else its body's base INI).
   Ammunition and darts stay untouched, because the engine treats quiver items as always
   equipped.
7. **Armour colours.** Body armour with look code `2A` (leather), `3A` (chain), `4A`
   (plate, full plate) or `2W`/`3W`/`4W` (robes) gets an equipped `op272` that attaches
   `HGA<code>.EFF` to the wearer once per second. That EFF's `op326` applies
   `HGA<code>.SPL` only to a creature with the marker state. The spell sets the metal and
   armor colour ranges, and for robes the cloak, for 3 seconds.
8. **Ability "Become a Hobgoblin" (`HGPCXFRM`).** An innate ability with the icons of the
   installed Polymorph Self (`SPWI416`, when present). It sets the permanent base
   animation (melee base INI), the base colours for skin, hair, leather and minor ranges
   from `HOBGOB.CRE`, race HOBGOBLIN and the marker state, then removes itself (`op172`).
9. **Handing out the ability.** A block on top of every world script that `CAMPAIGN.2DA`
   names (EET: `BALDUR`, `BALDUR25`, `BDBALDUR`; `BALDUR.BCS` when the table names none)
   applies `HGPCGIVE` (`op171`: learn `HGPCXFRM`) to Player1 once per game, when the
   protagonist is in the party, alive and not yet a hobgoblin. The global
   `CBPR_HOBGOBLIN_GIVEN` marks it as done, so new games and older saves both get it.
10. **Inventory figure.** `HGPMINV.BAM` and `HGPRINV.BAM` from `MHOBG1.BAM`: frame 0 of
    cycle 16 (standing, facing south) at twice the size, with the source palette, as a
    two-frame BAM (figure and a 1x1 blank) with one cycle `0, 0, 1`. The centre `-4, -16`
    is where the lab prototype sat right on the paperdoll. The blank pixel is the palette's
    transparent colour (the first `RGB(0,255,0)` entry, else entry 0, as the engine picks
    it) and the header keeps the source's RLE index, so a hobgoblin sprite from another
    mod that uses other indices for them still gives a clean figure.
11. **Voice set `CBPRHG`.** All ten hobgoblin clips of the game (`HOBGL01`-`HOBGL10`), each
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
- a WeiDU parse check of the tp2, every tpa and the tph, and the language file against
  every `@N` the sources use.

The tests include uninstall. Any WeiDU 249 or newer works, also a mod's `setup-*.exe`.

## Open

- A race in character creation, so the protagonist starts as a hobgoblin.
- Graphics per weapon group.
- Listening to the voice in a real game: the lab runs muted, so it checked subtitles and
  the engine's state, not the sound.
- More voice lines.
- Before a release: check the `HG*` resource names (`HGPM*`, `HGPR*`, `HGE*`, `HGA*`,
  `HGPC*`) and the voice set name `CBPRHG` against other mods.

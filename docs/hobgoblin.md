# Hobgoblin protagonist (component 100)

The component builds everything from the installed game: the hobgoblin animation INI
`8100.ini`, the `MHOB*` sprite files, `HOBGOB.CRE` colours, the game's item list, the
hobgoblin creatures' sound slots and the campaigns' world scripts.

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
11. **Voice set `CBPRHG`.** For each sound slot 1-34, the string most creatures with the
    hobgoblin animation (`0x8100`) use, ties to the lower string number. A slot whose
    chosen string has no sound file stays empty, as it is silent on those creatures too.
    The voice is laid out like an EE Soundset Tool voice:
    - Each chosen line's sound is copied as `CBPRHG` plus the slot's file character
      (battle cry 1 `a`, damage `l`, dying `m`, select 1 `f`, ...) into
      `lang/<language>/sounds`; two-character slots (`c_` for attack 1, ...) go to
      `override`.
    - Each line is resolved again with that sound and without a leading tag such as
      `[HOBGOBLIN 01]`.
    - The strings fill a `CHARSND.2DA` column, and `M_cdsnd.lua` gets the menu name
      "Hobgoblin"; other voice packs' lines stay as they are. A name counts as taken
      only on a line that sets `filenames_stringrefs['CBPRHG']` (either quote);
      commented-out lines and longer names that contain it do not.

    Rows 35 and up stay empty, because their meaning differs between BG:EE and BG2:EE.
    Without a voice set, and with a warning, nothing copied and nothing changed: when
    `CHARSND.2DA` lacks the 99 rows 1-99, or when the name is taken already (a `CBPRHG`
    column, a `CBPRHG` menu name in `M_cdsnd.lua`, or one of the sound files).

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

## Tests

`python tests/run_tests.py --weidu <weidu.exe>` runs the library's functions in small
synthetic game folders (made-up tables, strings, creatures, scripts and sprites; no game
needed):
- world-script discovery, and the shipped `give_ability.baf` compiled on top of the world
  scripts;
- the `CHARSND.2DA` check, sound lookup and voice-set registration, also next to other
  voice packs' menu lines;
- the creature vote with its sound files, and the cases where no voice set may be made;
- the inventory figure, also from sprites with other transparent and RLE indices;
- a WeiDU parse check of the tp2 and every tpa, and the language file against every
  `@N` the sources use.

The tests include uninstall. Any WeiDU 249 or newer works, also a mod's `setup-*.exe`.

## Open

- A race in character creation, so the protagonist starts as a hobgoblin.
- Graphics per weapon group.
- More voice lines.
- Before a release: check the `HG*` resource names (`HGPM*`, `HGPR*`, `HGE*`, `HGA*`,
  `HGPC*`) and the voice set name `CBPRHG` against other mods.

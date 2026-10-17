# Hobgoblin protagonist (component 100)

The component builds everything from the installed game: the hobgoblin animation INI
`8100.ini`, the `MHOB*` sprite files, `HOBGOB.CRE` colours and the game's item list.

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
8. **Transformation spell `HGPCXFRM`.** Permanent base animation (melee base INI), base
   colours for skin, hair, leather and minor ranges from `HOBGOB.CRE`, race HOBGOBLIN and
   the marker state.

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
- `move_scale` 9 walked about 8 % slower on this body than a human character animation at
  the same value (96.5 against 105.3 pixels per second). The vanilla `8100.ini` uses 5.

## Open

- An in-game way to become a hobgoblin.
- The inventory figure, built at install time from the game's files.
- A voice set from the game's own hobgoblin lines.
- Graphics per weapon group.
- A race in character creation.
- Before a release: check the `HG*` resource names (`HGPM*`, `HGPR*`, `HGE*`, `HGA*`,
  `HGPCXFRM`) against other mods.

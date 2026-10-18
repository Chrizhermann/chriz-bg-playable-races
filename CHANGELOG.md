# Changelog

## v0.2.0-proto (unreleased)

- Hobgoblin in character creation: race lists in every campaign offer the hobgoblin, with
  its own description and, where the UI builds the biography from `bioRaceData` (EET), its
  own biography; the record screen names the race **Hobgoblin**. The engine creates only its
  seven standard races (lab run 14b: race 111 got no class), so the choice creates a
  character with the rules of a template race, and the world scripts turn the protagonist
  into a hobgoblin as the game starts (`HGPCXNOW`).
- Two subcomponents for the template race: 100, half-orc rules (classes, ability
  adjustments and limits, thief skills); 101, human rules (any class; no dual-class once a
  hobgoblin, lab run 16c). After the transformation the hobgoblin keeps the template race's
  thief skill bonuses and has infravision, both as permanent effects of the transformation:
  the engine reads `SKILLRAC.2DA` and `RACEFEAT.2DA` only under the names of its seven
  races (lab runs 15c, 15d), so the installer adds no rows there. The engine counts the
  skill effects in the same classes and kits as a race's own row (lab run 16).
- Protagonists not created in this game's character creation (imported, older saves, or a
  UI without the routed race choice) still get the one-use ability; created with another
  race, they get nothing. The ability's description now says what the transformation
  changes: infravision and the template race's thief skill bonuses in place of the
  protagonist's own race's, and no dual-classing.
- Weapon groups: each melee look code is drawn as its weapon group (sword, axe, dagger,
  mace, morning star, flail, hammer, club, staff, spear, halberd, sling), with further
  sprite bodies (`HGP1`-`HGP9`) where codes of different groups share a first letter. With
  the generated weapon art (`tools/hob_weapon_art.py`) in `hobgoblin/weapons`, each group
  gets its own weapon layer, coloured with the game's palette; without it, or on a
  hobgoblin sprite with other frame geometry, every melee weapon shows the sword.
- Fixed: 2DA tables without data rows (the `CAMPAIGN.2DA` of BG:EE and BG2:EE 2.7) had
  their column names read as a data row.

## v0.1.1-proto (unreleased)

- Curated hobgoblin voice: all ten hobgoblin clips of the game, each on the event it fits
  (two order lines, two battle cries, two selection lines, hit, death, badly wounded, a
  party member's death; becoming leader and critical hits reuse an order line and a battle
  cry). v0.1 copied the creatures' own sound table, which left orders silent.
- The voice is registered with the EE Soundset Tool's `cd_add_soundset.tph`, shipped
  unchanged, like the voice packs in `chriz-bg-voicepacks`; subtitles come from the
  game's own strings.
- Updating from v0.1: choose the Hobgoblin voice again under Record > Customize > Voice.
  A character keeps the lines its voice had when it was chosen.

## v0.1.0-proto (2026-10-18)

- Innate ability "Become a Hobgoblin" (`HGPCXFRM`) for the protagonist, handed out once
  per game by the campaigns' world scripts (new games and older saves); it removes itself
  after use.
- The installer builds the inventory figure (`HGPMINV`, `HGPRINV`) from the game's
  hobgoblin sprite, also when another mod's sprite uses other palette indices.
- Hobgoblin voice set `CBPRHG` from the game's hobgoblin creatures, laid out like EE
  Soundset Tool voices (sound files in `lang/<language>/sounds`, `CHARSND.2DA` column,
  menu name in `M_cdsnd.lua` next to other voice packs' lines), so it shows in the voice
  menu.
- Offline tests (`tests/run_tests.py`) for the installer library in synthetic game
  folders, and a parse check of the shipped sources.

## v0.0.7-proto (2026-10-17)

First version in this repository. Earlier prototype versions were not kept in version
control.

- Hobgoblin protagonist as component 100 (`cbpr_hobgoblin_protagonist`), in a layout with
  room for more races.
- Weapon-driven sprites: one animation INI per pair of weapon look codes; every weapon
  switches the protagonist's sprite while selected.
- Armour colours by armour type, limited to the protagonist: the armour's effect checks the
  protagonist's marker state before it recolours.

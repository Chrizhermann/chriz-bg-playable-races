# Changelog

## v0.3.0-proto (unreleased)

- The hobgoblin is a race of its own: character creation creates race HOBGOBLIN (111) with its
  own rules, read from the race tables under the label `HOBGOBLIN`. An EEex hook
  (`race/M_CBPRRC.lua`, found through `race/CBPRRACE.db`) makes the engine give race 111 that
  label; without it the engine has labels for its seven races only. **Needs EEex** (lab: v1.2.0).
- The race's rules (The Complete Book of Humanoids, with Chris's changes; decided 2026-10-19):
  +1 Constitution, -1 Wisdom, -1 Charisma; Constitution 12-19, Strength and Dexterity at least 6;
  infravision; the human's thief skills with +5% Open Locks, +5% Find Traps, +10% Move Silently,
  +5% Hide in Shadows; the half-orc's classes, kits, mage schools and racial to-hit bonuses as
  the installed game has them (with a mod that opens all classes to all races, all of them);
  dual-class allowed; +1 to hit against elves (`op178`).
- The look: on top of the campaigns' world scripts, a block per party slot gives a hobgoblin with
  a character animation (character creation gives the race the human's) the hobgoblin's look and
  the race's spell effects (`HGPCRACE`). Every party member of race HOBGOBLIN gets them, not only
  the protagonist.
- Removed: component 101 (human rules), the template race, the routed race choice in `UI.MENU`
  (no `UI.MENU` change anymore), the transformation at game start (`HGPCXNOW`) and the ability
  handed out to protagonists (`HGPCGIVE`).
- Saves from v0.1 and v0.2: a protagonist made a hobgoblin keeps race 111 and now gets the race's
  rules from the tables; once per game, `HGPCRACE` replaces the old version's effects and adds the
  hatred of elves. `HGPCXFRM` stays, for saves whose protagonist still has the ability.
- The installer stops before changing anything without EEex (its hook functions, pattern folder
  and `EEex_LuaTrigger`), when `Baldur.exe` does not have the engine code the hook redirects
  exactly once, when `RACE.IDS` gives HOBGOBLIN a number the hook cannot label, when another mod
  has HOBGOBLIN entries in the race tables or a race 111 row in a race list of character
  creation, and when `ABRACEAD` or `ABRACERQ` lack a column the race sets.
- `lib/race_functions.tpa`: race tables read line by line (short rows, LF line ends, columns in any
  order), the pattern search in the executable, the race list of the hook.
  [docs/new-race-with-eeex.md](docs/new-race-with-eeex.md) explains the method for other races.
- Known issue, since v0.1: after loading a save, a hobgoblin holding a weapon other than a long
  sword or halberd shows no weapon until the weapon is changed (the engine applies the weapon's
  equipped effects before the marker state is in force; lab run 18b).

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
  sprite bodies (`HGP1`-`HGP9`) where codes of different groups share a first letter. Each
  group gets its own weapon layer from the weapon art shipped in `hobgoblin/weapons`,
  coloured with the game's palette; on a hobgoblin sprite with other frame geometry every
  melee weapon shows the sword.
- Weapon art: the mod's own drawing (`tools/hob_weapon_art.py`), each group's weapon drawn
  frame by frame where the game's hobgoblin holds its sword, with no game pixels and no
  palette. A test checks the shipped files. The installer stops before changing anything
  when the art is missing.
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

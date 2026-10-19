# Chriz BG Playable Races

Monster protagonists for the Baldur's Gate Enhanced Editions. Each component turns the
protagonist into a creature the game already has. The installer builds the sprites and
armour colours from your installed game's own files and draws the weapons with the mod's
own weapon art, so the mod ships no game art or audio.

**Status:** lab prototype `v0.3.0-proto`, not released. It has been tested only in a
disposable lab copy of one EET install (BG2:EE 2.7.3.0, EEex v1.2.0) and with the offline
tests.

## Components

| Component | Label | Purpose |
|---:|---|---|
| 100 | `cbpr_hobgoblin_book` | [Hobgoblin protagonist](docs/hobgoblin.md), rules of the book: -1 Charisma (needs EEex) |
| 101 | `cbpr_hobgoblin_strong` | [Hobgoblin protagonist](docs/hobgoblin.md), stronger rules: +1 Constitution, -1 Wisdom, -1 Charisma (needs EEex) |

Install one of the two: they build the same hobgoblin and differ only in its ability scores.

### 100 and 101: Hobgoblin protagonist

- Character creation offers **Hobgoblin** as a race of its own, with its own description and,
  in EET, its own biography. The race has its own rules, which the engine reads from its race
  tables; an EEex hook gives the race the label those tables use
  ([how it works](docs/new-race-with-eeex.md)).

  | | 100: rules of the book | 101: stronger |
  |---|---|---|
  | Ability scores | -1 Charisma | +1 Constitution, -1 Wisdom, -1 Charisma |
  | Limits | Strength and Dexterity at least 6; Constitution at least 5; Charisma at most 17 | Constitution 12-19; Strength and Dexterity at least 6; Wisdom and Charisma at most 17 |

  Both versions:

  | | Hobgoblin |
  |---|---|
  | Infravision | yes |
  | Hatred of elves | +1 to hit against elves |
  | Thief skills | the human's, with +5% Open Locks, +5% Find Traps, +10% Move Silently, +5% Hide in Shadows |
  | Classes and kits | the half-orc's in your game (with a mod that opens all classes to all races: all of them) |
  | Dual-class | yes |

  The values follow the hobgoblin of AD&D 2nd edition's *The Complete Book of Humanoids*, with
  Chris's changes: better Move Silently and Hide in Shadows, dual-classing, and in version 101
  +1 Constitution (12-19) and -1 Wisdom. The book's Charisma limit of 14 is left out, so
  paladins (17), bards and druids (15) stay possible. [docs/hobgoblin.md](docs/hobgoblin.md#the-rules)
  compares them.
- A hobgoblin looks like one: the game gives a new race the human's figure in character
  creation, so the world scripts give every party member of race Hobgoblin the hobgoblin's
  figure and colours as the game starts, and again after a dual-class.
- The inventory shows the hobgoblin as the paperdoll figure.
- A hobgoblin voice from the game's ten hobgoblin clips, each on the event it fits
  (orders and moving, battle cries, selection, hit, death, ...): choose **Hobgoblin** under
  Record > Customize > Voice.
- The sprite follows the active weapon. Each melee weapon is drawn as its group (sword, axe,
  dagger, mace, morning star, flail, hammer, club, staff, spear, halberd, sling), with the
  weapon art in `hobgoblin/weapons`. If another mod replaced the hobgoblin sprite with one
  whose frames differ, every melee weapon is drawn as a sword. Bows and crossbows are
  drawn as a bow, fists show no weapon, and two-handed weapons use the one-handed slash
  instead of the bow shot.
- Body armour recolours the hobgoblin: leather brown, chain grey, plate steel, robes
  purple and blue. Plate and full plate share one colour because the game gives both the
  same armour code. Without armour the protagonist's own colours return.
- Companions and other creatures keep their looks, even with the same weapons and armour.

Verified in the lab (latest: 2026-10-19, runs 18-18c, on a copy of a full EET install with
Artisan's Kitpack opening all classes to all races):

- At game start the console reported the race hook active for HOBGOBLIN (111).
- Character creation listed the hobgoblin with its description, and offered it the half-orc's
  21 classes and the same thief kits. 3,000 ability rolls of a thief stayed within
  Constitution 12-19, Strength 6-18 and Wisdom and Charisma 3-17.
- A hobgoblin thief started the game as a hobgoblin, with infravision, the +1 to hit against
  elves and the race's thief skills: 21/21/16/26/16/15/5 for 6/6/6/6/6/5/5 spent points. The
  record screen named the race **Hobgoblin**.
- At thief level 2 it could dual-class; as a Fighter/Thief it stayed a hobgoblin, in race and
  looks.
- Saving and reloading kept the race, the looks, the marker that limits the weapon and armour
  looks to hobgoblins, and the hook.
- Saves of v0.1 and v0.2 with a hobgoblin protagonist: after loading, the protagonist had the
  race's rules and the hatred of elves, and v0.2's own skill effects were gone, so nothing
  counted twice.
- Uninstall restored every file under `override` and `EEex_scripts` byte for byte.
- Earlier runs (v0.1, v0.2): all 19 test weapons gave the sprite their group's look; the
  armour colours, the inventory figure and the voice worked; only hobgoblins changed, the
  companions kept their sprites.

Not done yet:

- After loading a save, a hobgoblin holding a weapon other than a long sword or halberd shows
  no weapon until the weapon is changed (since v0.1).
- Not tested with EEex v1.3.1, BG:EE or SoD outside EET, or other game versions.
- The voice has only the ten clips the game's hobgoblins have, so it repeats itself
  more than a full voice pack.

## Installation (testers)

1. Install [EEex](https://github.com/Bubb13/EEex) first (v1.2.0 tested).
2. Copy `setup-chriz-bg-playable-races.tp2` and the `chriz-bg-playable-races` folder into
   the game folder.
3. Put a current [WeiDU](https://github.com/WeiDUorg/weidu/releases) next to them, named
   `setup-chriz-bg-playable-races.exe`.
4. Run it and choose one version of the hobgoblin: 100 (rules of the book) or 101 (stronger).

Install it after mods that add weapons or armour, so that their items get the hobgoblin
looks too, and after mods that change the half-orc's classes, kits and other race tables
(such as a mod that opens all classes to all races), so that the hobgoblin follows them.

The component stops before it changes anything when the game lacks EEex, when `Baldur.exe`
does not have the engine code the hook redirects (it supports BG:EE, SoD, BG2:EE and EET
2.7.3.0), when another mod already made HOBGOBLIN a race of its own, when the game's
hobgoblin animation (`8100.ini`, `MHOB*.BAM`) is missing, and when the mod's own weapon art is
missing (an incompletely unpacked mod).

To remove it, run `setup-chriz-bg-playable-races.exe` again and choose Uninstall, before
you install other mods on top. WeiDU puts back every file the component changed and
deletes the ones it added (keep the `chriz-bg-playable-races` folder until then: it holds
the backup). Left over are WeiDU's own `.DEBUG` log, a comment in `WeiDU.log` and the
component's strings in `dialog.tlk` (WeiDU leaves added strings in place).
Saves made while the component was installed keep its changes: after an uninstall a
hobgoblin keeps race 111 and the plain hobgoblin sprite, but the engine then has no rules
and no name for that race. So back up your save folder before you try the component, and
put it back after an uninstall.

To update from v0.1 or v0.2, uninstall it as above while its own files are still in place,
then unpack the new version over them and install it. A protagonist made a hobgoblin by v0.1
or v0.2 keeps being one and gets the race's rules. For a protagonist that had v0.1's voice,
choose **Hobgoblin** again under Record > Customize > Voice: the game copies a voice's lines
into the character when the voice is chosen.

## Tests

```
python tests/run_tests.py --weidu path/to/weidu.exe
```

The tests run the installer library with WeiDU in small synthetic game folders; no game
or game files are needed. See [docs/hobgoblin.md](docs/hobgoblin.md#tests).

## Game files and voices

Everything game-derived is built on the player's machine from their own copy of the game.
Sprites, inventory figures and sounds made from game files never enter this repository.
Voice lines made with voice cloning are not part of it either.

The weapon art in `chriz-bg-playable-races/hobgoblin/weapons` is the mod's own drawing,
made with `tools/hob_weapon_art.py`. The tool draws each weapon, frame by frame, where the
game's hobgoblin holds its sword. The files contain no game pixels and no palette; the
installer colours them with the palette of the game's own hobgoblin sword.

The voice is registered with `lib/cd_add_soundset.tph` from the
[EE Soundset Tool](https://github.com/Gibberlings3/EE_soundset_tool) by CamDawg and Graion
Dilach, shipped unchanged and not covered by this repository's license.

## License

The mod's code is MIT licensed, see [LICENSE](LICENSE). Baldur's Gate and its assets
belong to their owners; this project is not affiliated with Beamdog, BioWare or Wizards of
the Coast.

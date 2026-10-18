# Chriz BG Playable Races

Monster protagonists for the Baldur's Gate Enhanced Editions. Each component turns the
protagonist into a creature the game already has. The installer builds the sprites,
weapon looks and armour colours from your installed game's own files, so the mod ships no
game art or audio.

**Status:** lab prototype `v0.2.0-proto`, not released. It has been tested only in a
disposable lab copy of one EET install (BG2:EE 2.7.3.0) and with the offline tests.

## Components

| Component | Label | Purpose |
|---:|---|---|
| 100 | `cbpr_hobgoblin_protagonist` | [Hobgoblin protagonist](docs/hobgoblin.md), half-orc rules |
| 101 | `cbpr_hobgoblin_protagonist_human_rules` | [Hobgoblin protagonist](docs/hobgoblin.md), human rules |

Install one of the two: they differ only in the rules character creation uses for the
hobgoblin.

### 100 and 101: Hobgoblin protagonist

- Character creation offers **Hobgoblin** as a race, with its own description and, in EET,
  its own biography. The engine can only create its seven standard races, so the
  hobgoblin is made with a template race's rules: the half-orc's (100: classes, ability
  adjustments and limits, thief skills) or the human's (101: any class). Character
  creation shows the template race; the protagonist becomes a hobgoblin, in looks and
  race, as soon as the game starts.
- As a hobgoblin it keeps the template race's thief skill bonuses, in each class and kit
  just as the game gives them to that race, and has infravision. Unlike a human, it cannot
  dual-class.
- A protagonist that was not created in the game's character creation (imported, or from
  a save made before the install) gets the innate ability **Become a Hobgoblin** instead.
  It works once and for good: hobgoblin sprite, race HOBGOBLIN with the template race's
  thief skill bonuses and infravision, then the ability is gone.
- The inventory shows the hobgoblin as the paperdoll figure.
- A hobgoblin voice from the game's ten hobgoblin clips, each on the event it fits
  (orders and moving, battle cries, selection, hit, death, ...): choose **Hobgoblin** under
  Record > Customize > Voice.
- The sprite follows the active weapon. Each melee weapon is drawn as its group (sword, axe,
  dagger, mace, morning star, flail, hammer, club, staff, spear, halberd, sling) when the
  weapon art is in `hobgoblin/weapons`; without it, every melee weapon is drawn as a sword.
  Bows and crossbows are drawn as a bow, fists show no weapon, and two-handed weapons use
  the one-handed slash instead of the bow shot.
- Body armour recolours the hobgoblin: leather brown, chain grey, plate steel, robes
  purple and blue. Plate and full plate share one colour because the game gives both the
  same armour code. Without armour the protagonist's own colours return.
- Companions and other creatures keep their looks, even with the same weapons and armour.

Verified in the lab on 2026-10-17 and 2026-10-18:

- In a save made before the install, the protagonist got the ability once and the
  companions got nothing. Using it made the protagonist a hobgoblin and removed the
  ability.
- Only the protagonist changed. The five companions kept their sprites at load, after
  the transformation, with patched weapons and after saving and reloading.
- Weapon changes worked through scripts and through the action bar.
- All 19 test weapons (five swords, axe, dagger, club, flail, mace, morning star, hammer,
  staff, spear, halberd, sling, two bows, a crossbow) gave the sprite their group's look,
  with whole shafts on staff, spear and halberd.
- Character creation listed the hobgoblin among the races, with its description and its
  biography. A thief created as a hobgoblin started the game as one, with infravision and
  the thief skills character creation had shown: 21/16/16/16/11/10/5 with half-orc rules,
  21/16/11/16/11/15/5 with human rules, for the same points.
- The thief skill bonuses counted in the same classes as the template race's own: checked
  for thief, fighter, bard, Blade, ranger, monk and shaman.
- At level 2 the record screen offered dual-classing to the character as a human, not as a
  hobgoblin.
- The record screen showed the race Hobgoblin, and the inventory the hobgoblin figure the
  installer builds.
- **Hobgoblin** was listed under Record > Customize > Voice. Choosing it gave the
  protagonist the twelve lines of the voice table. Every selection and every move order
  played a line; attack orders played a battle cry now and then, as the companions'
  battle cries do. (Checked through subtitles: the lab runs without sound.)
- Saving and reloading kept the sprite, the race, the voice and the marker that limits
  the effects to the protagonist.
- Armour already worn in an older save worked right after loading.

Not done yet:

- The weapon art is not in the repository yet. `tools/hob_weapon_art.py` draws it from an
  installed game's hobgoblin sprites.
- The voice has only the ten clips the game's hobgoblins have, so it repeats itself
  more than a full voice pack.

## Installation (testers)

1. Copy `setup-chriz-bg-playable-races.tp2` and the `chriz-bg-playable-races` folder into
   the game folder.
2. Put a current [WeiDU](https://github.com/WeiDUorg/weidu/releases) next to them, named
   `setup-chriz-bg-playable-races.exe`.
3. Run it and choose component 100 (half-orc rules) or 101 (human rules).

Install it after mods that add weapons or armour, so that their items get the hobgoblin
looks too, and after mods that replace `UI.MENU` (UI mods), so that character creation can
offer the hobgoblin. The transformation cannot be undone in the game, so save before you
use the ability.

To remove it, run `setup-chriz-bg-playable-races.exe` again and choose Uninstall, before
you install other mods on top. WeiDU puts back every file the component changed and
deletes the ones it added (keep the `chriz-bg-playable-races` folder until then: it holds
the backup). In a lab check on a copy of a full EET install, all game files matched their
state before the install afterwards. Left over were WeiDU's own `.DEBUG` log, a comment in
`WeiDU.log` and the component's strings in `dialog.tlk` (WeiDU leaves added strings in
place).
Saves made while the component was installed keep its changes: after an uninstall, a
transformed protagonist stays a hobgoblin, with the plain hobgoblin sprite, no inventory
figure, no race name and a silent voice. So back up your save folder before you try the
component, and put it back after an uninstall.

To update from v0.1, uninstall it as above while its own files are still in place, then
unpack the new version over them and install it. Then choose **Hobgoblin** again under
Record > Customize > Voice for a protagonist that already had the voice: the game copies a
voice's lines into the character when the voice is chosen, so such a protagonist keeps
v0.1's six lines, which now play the new sound files under v0.1's subtitles and leave
orders silent.

The component needs the game's hobgoblin animation (`8100.ini`, `MHOB*.BAM`) and
stops with a message when it is missing. EEex is not required; the lab uses it only for
testing.

## Tests

```
python tests/run_tests.py --weidu path/to/weidu.exe
```

The tests run the installer library with WeiDU in small synthetic game folders; no game
or game files are needed. See [docs/hobgoblin.md](docs/hobgoblin.md#tests).

## Game files and voices

Everything game-derived is built on the player's machine from their own copy of the game.
Files generated from game data (sprites, inventory figures, sounds) never enter this
repository. Voice lines made with voice cloning are not part of it either.

The voice is registered with `lib/cd_add_soundset.tph` from the
[EE Soundset Tool](https://github.com/Gibberlings3/EE_soundset_tool) by CamDawg and Graion
Dilach, shipped unchanged and not covered by this repository's license.

## License

The mod's code is MIT licensed, see [LICENSE](LICENSE). Baldur's Gate and its assets
belong to their owners; this project is not affiliated with Beamdog, BioWare or Wizards of
the Coast.

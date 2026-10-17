# Chriz BG Playable Races

Monster protagonists for the Baldur's Gate Enhanced Editions. Each component turns the
protagonist into a creature the game already has. The installer builds the sprites,
weapon looks and armour colours from your installed game's own files, so the mod ships no
game art or audio.

**Status:** lab prototype `v0.1.0-proto`, not released. It has been tested only in a
disposable lab copy of one EET install (BG2:EE 2.7.3.0) and with the offline tests. The
protagonist becomes a hobgoblin through an innate ability; a race in character creation
comes later.

## Components

| Component | Label | Purpose |
|---:|---|---|
| 100 | `cbpr_hobgoblin_protagonist` | [Hobgoblin protagonist](docs/hobgoblin.md) |

### 100: Hobgoblin protagonist

- The protagonist gets the innate ability **Become a Hobgoblin**, in a new game and in a
  save made before the install. It works once and for good: hobgoblin sprite, race
  HOBGOBLIN, then the ability is gone.
- The inventory shows the hobgoblin as the paperdoll figure.
- A hobgoblin voice from the game's own hobgoblin lines: choose **Hobgoblin** under
  Record > Customize > Voice.
- The sprite follows the active weapon. For now every melee weapon is drawn as a sword
  and every bow or crossbow as a bow. Fists and slings show no weapon, and two-handed
  weapons use the one-handed slash instead of the bow shot.
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
- The record screen showed the race HOBGOBLIN, and the inventory the hobgoblin figure the
  installer builds.
- **Hobgoblin** was listed under Record > Customize > Voice. Choosing it gave the
  protagonist the voice set's lines.
- Saving and reloading kept the sprite, the race, the voice and the marker that limits
  the effects to the protagonist.
- Armour already worn in an older save worked right after loading.

Not done yet:

- No race in character creation: the protagonist starts human (or whatever was chosen)
  and becomes a hobgoblin through the ability.
- Weapon groups have no own graphics yet.
- The voice has only the lines the game's hobgoblins have: two battle cries, two
  selection lines, a pain and a death sound.

## Installation (testers)

1. Copy `setup-chriz-bg-playable-races.tp2` and the `chriz-bg-playable-races` folder into
   the game folder.
2. Put a current [WeiDU](https://github.com/WeiDUorg/weidu/releases) next to them, named
   `setup-chriz-bg-playable-races.exe`.
3. Run it and choose component 100.

Install it after mods that add weapons or armour, so that their items get the hobgoblin
looks too. The transformation cannot be undone in the game, so save before you use the
ability.

To remove it, run `setup-chriz-bg-playable-races.exe` again and choose Uninstall, before
you install other mods on top. WeiDU puts back every file the component changed and
deletes the ones it added (keep the `chriz-bg-playable-races` folder until then: it holds
the backup). In a lab check on a copy of a full EET install, all game files matched their
state before the install afterwards. Left over were WeiDU's own `.DEBUG` log, a comment in
`WeiDU.log` and the component's ten strings in `dialog.tlk`, which nothing uses any more.
Saves made while the component was installed keep its changes: after an uninstall, a
transformed protagonist stays a hobgoblin, with the plain hobgoblin sprite, no inventory
figure, no race name and a silent voice. So back up your save folder before you try the
component, and put it back after an uninstall. The component needs the game's hobgoblin animation (`8100.ini`, `MHOB*.BAM`) and
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

## License

The mod's code is MIT licensed, see [LICENSE](LICENSE). Baldur's Gate and its assets
belong to their owners; this project is not affiliated with Beamdog, BioWare or Wizards of
the Coast.

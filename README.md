# Chriz BG Playable Races

Monster protagonists for the Baldur's Gate Enhanced Editions. Each component turns the
protagonist into a creature the game already has. The installer builds the sprites,
weapon looks and armour colours from your installed game's own files, so the mod ships no
game art or audio.

**Status:** lab prototype `v0.0.7-proto`, not released. It has been tested only in a
disposable lab copy of one EET install (BG2:EE 2.7.3.0). A normal game has no way yet to
turn the protagonist into a hobgoblin.

## Components

| Component | Label | Purpose |
|---:|---|---|
| 100 | `cbpr_hobgoblin_protagonist` | [Hobgoblin protagonist](docs/hobgoblin.md) |

### 100: Hobgoblin protagonist

- The protagonist uses the hobgoblin sprite and the race HOBGOBLIN.
- The sprite follows the active weapon. For now every melee weapon is drawn as a sword
  and every bow or crossbow as a bow. Fists and slings show no weapon, and two-handed
  weapons use the one-handed slash instead of the bow shot.
- Body armour recolours the hobgoblin: leather brown, chain grey, plate steel, robes
  purple and blue. Plate and full plate share one colour because the game gives both the
  same armour code. Without armour the protagonist's own colours return.
- Companions and other creatures keep their looks, even with the same weapons and armour.

Verified in the lab on 2026-10-17:

- Only the protagonist changed. The five companions kept their sprites at load, after
  the transformation, with patched weapons and after saving and reloading.
- Weapon changes worked through scripts and through the action bar.
- The record screen showed the race HOBGOBLIN. The inventory showed the hobgoblin with a
  figure made by a separate prototype step (see below).
- Saving and reloading kept the sprite, the race and the marker that limits the effects
  to the protagonist.
- Armour already worn in an older save worked right after loading.

Not done yet:

- There is no in-game way to become a hobgoblin. The lab applies the spell `HGPCXFRM`.
- The installer does not build the inventory figure yet.
- There is no hobgoblin voice set and no race in character creation.
- Weapon groups have no own graphics yet.

## Installation (testers)

1. Copy `setup-chriz-bg-playable-races.tp2` and the `chriz-bg-playable-races` folder into
   the game folder.
2. Put a current [WeiDU](https://github.com/WeiDUorg/weidu/releases) next to them, named
   `setup-chriz-bg-playable-races.exe`.
3. Run it and choose component 100.

The component needs the game's hobgoblin animation (`8100.ini`, `MHOB*.BAM`) and stops
with a message when it is missing. EEex is not required; the lab uses it only for testing.

## Game files and voices

Everything game-derived is built on the player's machine from their own copy of the game.
Files generated from game data (sprites, inventory figures, sounds) never enter this
repository. Voice lines made with voice cloning are not part of it either.

## License

The mod's code is MIT licensed, see [LICENSE](LICENSE). Baldur's Gate and its assets
belong to their owners; this project is not affiliated with Beamdog, BioWare or Wizards of
the Coast.

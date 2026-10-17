# Changelog

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

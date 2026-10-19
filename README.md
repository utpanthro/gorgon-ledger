# Gorgon Ledger

A local-first checklist and progress tracker for the MMORPG
[Project: Gorgon](https://projectgorgon.com/).

## Features

- Skill levels, milestone rewards, abilities, and recipe checklists
- NPC favor levels and NPC-specific quest tracking
- A searchable, zone-grouped quest ledger
- Gourmand food tracking with level requirements and acquisition sources
- Teleportation-circle tracking by zone
- File-backed local saves that are shared across browsers on this computer

## Run locally

On Windows, double-click **`Start Gorgon Ledger.cmd`**. The launcher starts the
local server and opens:

```text
http://127.0.0.1:4173/
```

Keep the launcher window open while using the tracker. Press `Ctrl+C` in that
window to stop it.

Python 3 is required. The launcher automatically checks `py`, `python`, and the
Python runtime bundled with Codex.

## Save data

Progress is written to:

```text
save-data/gorgon-ledger.json
```

The save directory is intentionally ignored by Git so personal game progress is
never committed. Browser storage is retained as a fallback and is migrated into
the save file automatically when the app loads.

## Project data

The tracker data is generated from the
[Project: Gorgon Wiki](https://wiki.projectgorgon.com/). Data-refresh utilities
live in `work/`; generated JSON files are stored with the feature that uses them.

## Website structure

- `src/skills/` contains the skill ledger, skill profiles, rewards, recipes, and teleport data.
- `src/foods/` contains the Gourmand ledger and food data.
- `src/npcs/` contains the NPC ledger, NPC profiles, quest data, and zone data.
- `src/quests/` contains the cross-NPC quest ledger.
- `src/shared/` contains browser code shared by every section.
- `src/assets/` contains shared visual assets.

## Repository notes

- `server.py` serves the website and provides the local save API.
- `src/shared/storage.js` synchronizes tracker state with the local save file.
- `src/` is the website root served by `server.py`.
- `src/index.html` redirects the root URL to the skill ledger at `/skills/`.
- Dependencies and generated build output are excluded through `.gitignore`.

This is an unofficial community tool and is not affiliated with Elder Game,
LLC.

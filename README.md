# Grain Rot Mod Patcher

A standalone, lightweight synchronization toolchain for updating custom **Grain Rot** mods and UE4SS files directly from a remote GitHub repository.

---

## Features

- **Multiplayer Expansion Ready**: Pre-configured with `GrainRotTogether` to increase lobby size from 4 up to 12 (or 16) players.
- **Online-Fix & Steam Compatible**: Works seamlessly with Steam copies and Online-Fix standalone builds without hook conflicts.
- **Automatic Self-Update**: Automatically fetches the latest version of `grain_rot_patcher.bat` / `grain_rot_patcher.py` directly from GitHub before synchronizing mods.
- **Zero-Dependency Native Batch Script (`grain_rot_patcher.bat`)**:
  - Uses Windows built-in `curl.exe` and `tar.exe`.
  - No Python or third-party tools required for players.
- **Smart Directory Detection**:
  - Automatically discovers Grain Rot across Steam, Online-Fix, Repacks (`C:\Games\Grain Rot`, `Downloads`, `Desktop`, etc.).
  - Includes a Windows folder browser fallback dialog.
- **Python Alternative (`grain_rot_patcher.py`)**:
  - Clean cross-platform script using standard library with download progress indicators.

---

## Quick Start for Players

1. Download [`grain_rot_patcher.bat`](grain_rot_patcher.bat) from the latest release or root of this repository.
2. Double-click `grain_rot_patcher.bat`.
3. Press `[ENTER]` to confirm the detected game folder.
4. Once patching finishes, press `[ENTER]` to launch Grain Rot!

---

## Guide for Repository Maintainers

### 1. Configure Your GitHub Info
Open `grain_rot_patcher.bat` and `grain_rot_patcher.py` and set your GitHub details:

```bat
set "REPO_USER=hayagerwin"
set "REPO_NAME=gr-mods-patcher"
set "BRANCH=main"
```

```python
REPO_USER = "hayagerwin"
REPO_NAME = "gr-mods-patcher"
BRANCH = "main"
```

### 2. Updating / Rebuilding `patch.zip`
Whenever you update mods in your game or in r2modman:
1. Run:
   ```cmd
   python rebuild_patch.py
   ```
2. This will:
   - Synchronize the latest mod files and signatures from r2modman / game folder into `Helden/Binaries/Win64/...`.
   - Build a clean `patch.zip`.
   - Automatically bump the version timestamp in `grain_rot_patcher.bat` and `grain_rot_patcher.py`.
   - Update `patch_info.txt`.
3. Commit and push the changes to GitHub:
   ```cmd
   git add .
   git commit -m "Update mod patch"
   git push origin main
   ```
4. All players running `grain_rot_patcher.bat` will automatically receive the update!

---

## Mod Configuration

To customize lobby limits or other settings:
- Open `Helden\Binaries\Win64\Mods\Konologic-GrainRotTogether\config.ini`:
  ```ini
  MaxPlayers = 12
  Verbose = 0
  ```
  *(Supported range: 2 to 16 players. Only the lobby host needs this mod installed.)*

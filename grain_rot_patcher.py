#!/usr/bin/env python3
"""
Grain Rot Mod Patcher (Python Alternative)
Synchronizes custom mods and UE4SS files from a remote GitHub repository.
"""

import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
import urllib.request
import urllib.error

# ==============================================================================
# REPOSITORY CONFIGURATION
# Configure your GitHub username, repository name, and branch below.
# ==============================================================================
REPO_USER = "hayagerwin"
REPO_NAME = "gr-mods-patcher"
BRANCH = "main"
PATCHER_VERSION = "20260901092247"

# ==============================================================================
# TERMINAL FORMATTING HELPERS
# ==============================================================================
class Style:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

if sys.platform == "win32":
    os.system("")

def log_header(title: str):
    print(f"\n{Style.BOLD}{Style.CYAN}{'=' * 75}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}{title.center(75)}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}{'=' * 75}{Style.RESET}\n")

def log_step(step: str, message: str):
    print(f"{Style.BOLD}{Style.BLUE}[{step}]{Style.RESET} {message}")

def log_success(message: str):
    print(f"\n{Style.BOLD}{Style.GREEN}[SUCCESS]{Style.RESET} {message}")

def log_error(message: str):
    print(f"\n{Style.BOLD}{Style.RED}[ERROR]{Style.RESET} {message}")

def log_info(message: str):
    print(f"  {Style.YELLOW}->{Style.RESET} {message}")

def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")

# ==============================================================================
# CORE OPERATIONS
# ==============================================================================
_PATCHER_STATUS_TEXT = ""

def check_self_update(script_url: str):
    global _PATCHER_STATUS_TEXT
    if os.environ.get("_GR_PATCHER_SELF_UPDATED") == "1":
        _PATCHER_STATUS_TEXT = f"{Style.GREEN}[JUST UPDATED] (Successfully updated from GitHub){Style.RESET}"
        return

    current_script = Path(__file__).resolve()
    try:
        if (current_script.parent / ".git").is_dir():
            _PATCHER_STATUS_TEXT = f"{Style.CYAN}[DEV MODE] (Build {PATCHER_VERSION} - Git Working Copy){Style.RESET}"
            return

        print(f"{Style.CYAN}[1/2]{Style.RESET} Checking for patcher script updates on GitHub...")
        api_url = f"https://api.github.com/repos/{REPO_USER}/{REPO_NAME}/contents/grain_rot_patcher.py?ref={BRANCH}"
        remote_bytes = None
        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "GrainRot-Mods-Patcher-Client",
                    "Accept": "application/vnd.github.v3.raw"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                remote_bytes = response.read()
        except Exception:
            pass

        if remote_bytes is None:
            remote_url = f"{script_url}?t={os.urandom(4).hex()}"
            req = urllib.request.Request(
                remote_url,
                headers={
                    "User-Agent": "GrainRot-Mods-Patcher-Client",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                remote_bytes = response.read()

        remote_text = remote_bytes.decode("utf-8", errors="ignore").replace("\r\n", "\n").strip()
        local_text = current_script.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").strip()

        if remote_text != local_text:
            print(f"     {Style.YELLOW}[UPDATE AVAILABLE]{Style.RESET} Newer script version detected on GitHub.")
            print(f"     {Style.CYAN}[+] Downloading and replacing script...{Style.RESET}\n")

            current_script.write_bytes(remote_bytes)
            env = os.environ.copy()
            env["_GR_PATCHER_SELF_UPDATED"] = "1"
            exit_code = subprocess.call([sys.executable, str(current_script)] + sys.argv[1:], env=env)
            sys.exit(exit_code)
        else:
            print(f"     {Style.GREEN}[UP TO DATE]{Style.RESET} Running latest build {PATCHER_VERSION} (No update needed)\n")
            _PATCHER_STATUS_TEXT = f"{Style.GREEN}[UP TO DATE] (Build {PATCHER_VERSION} - Synced with GitHub){Style.RESET}"

    except Exception:
        print(f"     \033[90m[OFFLINE / LOCAL]\033[0m Running local build {PATCHER_VERSION}\n")
        _PATCHER_STATUS_TEXT = f"\033[90m[OFFLINE / LOCAL] (Build {PATCHER_VERSION})\033[0m"

def get_config_path() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            return Path(appdata) / "GrainRotModsPatcher" / "game_path.txt"
    return Path.home() / ".config" / "grain-rot-mods-patcher" / "game_path.txt"

def is_valid_grain_rot_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    if (p / "Helden.exe").is_file():
        return True
    if (p / "Helden" / "Binaries" / "Win64" / "Helden-Win64-Shipping.exe").is_file():
        return True
    return False

def open_folder_dialog() -> str:
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object Windows.Forms.FolderBrowserDialog; "
            "$f.Description = 'Select your Grain Rot game folder'; "
            "if($f.ShowDialog() -eq 'OK'){ $f.SelectedPath }"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return res.stdout.strip()
    except Exception:
        return ""

def locate_game_directory() -> Path:
    script_dir = Path(__file__).resolve().parent
    if is_valid_grain_rot_dir(script_dir):
        return script_dir

    cfg_file = get_config_path()
    candidates = []
    seen = set()

    if cfg_file.is_file():
        try:
            saved_str = cfg_file.read_text(encoding="utf-8").strip().strip('"')
            saved_p = Path(saved_str)
            if is_valid_grain_rot_dir(saved_p):
                norm = str(saved_p.resolve())
                seen.add(norm)
                candidates.append((saved_p, "Saved Location"))
        except Exception:
            pass

    # Drives scan
    drives = ["C:", "D:", "E:", "F:", "G:"] if sys.platform == "win32" else ["/"]
    for d in drives:
        std_paths = [
            Path(f"{d}/Games/Grain Rot"),
            Path(f"{d}/Games/GrainRot"),
            Path(f"{d}/SteamLibrary/steamapps/common/Grain Rot"),
            Path(f"{d}/Steam/steamapps/common/Grain Rot"),
            Path(f"{d}/Program Files (x86)/Steam/steamapps/common/Grain Rot"),
            Path(f"{d}/Program Files/Steam/steamapps/common/Grain Rot"),
        ]
        for sp in std_paths:
            if is_valid_grain_rot_dir(sp):
                norm = str(sp.resolve())
                if norm not in seen:
                    seen.add(norm)
                    candidates.append((sp, "Standard Install"))

        games_dir = Path(f"{d}/Games")
        if games_dir.is_dir():
            try:
                for item in games_dir.iterdir():
                    if item.is_dir() and "grain" in item.name.lower():
                        if is_valid_grain_rot_dir(item):
                            norm = str(item.resolve())
                            if norm not in seen:
                                seen.add(norm)
                                candidates.append((item, f"Found on {d}/Games"))
            except Exception:
                pass

    # User folders
    user_home = Path.home()
    for sub in ["Downloads", "Desktop", "Documents"]:
        u_dir = user_home / sub
        if u_dir.is_dir():
            try:
                for item in u_dir.iterdir():
                    if item.is_dir() and "grain" in item.name.lower():
                        if is_valid_grain_rot_dir(item):
                            norm = str(item.resolve())
                            if norm not in seen:
                                seen.add(norm)
                                candidates.append((item, f"Found in {sub}"))
            except Exception:
                pass

    if len(candidates) == 1:
        chosen, label = candidates[0]
        print(f"{Style.CYAN}[2/2]{Style.RESET} Auto-detected Grain Rot directory:")
        print(f"     {Style.GREEN}{chosen}{Style.RESET} {Style.BOLD}\033[90m({label})\033[0m")
        choice = input(f"\nPress {Style.BOLD}[ENTER]{Style.RESET} to proceed, or {Style.YELLOW}[C]{Style.RESET} to change path: ").strip().lower()
        if choice != "c":
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text(str(chosen.resolve()), encoding="utf-8")
            return chosen

    elif len(candidates) > 1:
        print(f"{Style.CYAN}[2/2]{Style.RESET} Multiple Grain Rot installations detected:")
        for idx, (c_path, c_label) in enumerate(candidates, 1):
            print(f"     {Style.BOLD}[{idx}]{Style.RESET} {c_path} \033[90m({c_label})\033[0m")
        sel = input(f"\nSelect [1-{len(candidates)}] or [B] to browse: ").strip().lower()
        if sel != "b":
            try:
                i = int(sel) - 1
                if 0 <= i < len(candidates):
                    chosen = candidates[i][0]
                    cfg_file.parent.mkdir(parents=True, exist_ok=True)
                    cfg_file.write_text(str(chosen.resolve()), encoding="utf-8")
                    return chosen
            except Exception:
                pass

    # Fallback picker
    while True:
        raw = input(f"\n{Style.YELLOW}[*]{Style.RESET} Drag-and-drop your Grain Rot game folder here, or press {Style.BOLD}[B]{Style.RESET} to browse: ").strip().strip('"\'')
        if raw.lower() == "b":
            raw = open_folder_dialog()

        if raw:
            p = Path(raw)
            if is_valid_grain_rot_dir(p):
                cfg_file.parent.mkdir(parents=True, exist_ok=True)
                cfg_file.write_text(str(p.resolve()), encoding="utf-8")
                return p

            # check child dirs
            if p.is_dir():
                for child in p.iterdir():
                    if child.is_dir() and is_valid_grain_rot_dir(child):
                        cfg_file.parent.mkdir(parents=True, exist_ok=True)
                        cfg_file.write_text(str(child.resolve()), encoding="utf-8")
                        return child

        print(f"{Style.RED}[ERROR] Invalid Grain Rot folder. Helden.exe not found.{Style.RESET}")

def download_with_progress(url: str, output_path: Path):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GrainRot-Mods-Patcher-Client", "Cache-Control": "no-cache", "Pragma": "no-cache"}
    )
    with urllib.request.urlopen(req, timeout=30) as response, open(output_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 65536
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size > 0:
                percent = downloaded * 100 / total_size
                mb_curr = downloaded / (1024 * 1024)
                mb_tot = total_size / (1024 * 1024)
                sys.stdout.write(f"\r     Downloading: {percent:5.1f}% [{mb_curr:5.2f}MB / {mb_tot:5.2f}MB]")
                sys.stdout.flush()
        print()

def check_game_running():
    while True:
        try:
            res = subprocess.run(["tasklist"], capture_output=True, text=True)
            if "helden-win64-shipping.exe" in res.stdout.lower() or "helden.exe" in res.stdout.lower():
                print(f"\n{Style.YELLOW}[WARNING] Grain Rot is currently running!{Style.RESET}")
                print("Mod files cannot be updated while the game is open.")
                choice = input(f"Please close Grain Rot, then press {Style.BOLD}[ENTER]{Style.RESET} to retry (or {Style.RED}[K]{Style.RESET} to force close): ").strip().lower()
                if choice == "k":
                    subprocess.run(["taskkill", "/f", "/im", "Helden-Win64-Shipping.exe"], capture_output=True)
                    subprocess.run(["taskkill", "/f", "/im", "Helden.exe"], capture_output=True)
                continue
        except Exception:
            pass
        break

def main():
    log_header("Grain Rot Mod Patcher")
    script_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/{BRANCH}/grain_rot_patcher.py"
    check_self_update(script_url)

    game_dir = locate_game_directory()
    clear_screen()

    log_header("Grain Rot Mod Patcher")
    if _PATCHER_STATUS_TEXT:
        print(_PATCHER_STATUS_TEXT)
    print(f"\033[90mTarget Folder:\033[0m {Style.BOLD}{game_dir}{Style.RESET}\n")

    # Stage 1: Deletion
    log_step("1/3", "Checking for deprecated mods...")
    del_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/{BRANCH}/delete_list.txt"
    try:
        req = urllib.request.Request(del_url, headers={"User-Agent": "GrainRot-Mods-Patcher-Client"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            lines = resp.read().decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                target = game_dir / line
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink(missing_ok=True)
                    print(f"     {Style.YELLOW}[-]{Style.RESET} Removed obsolete: {line}")
    except Exception:
        pass
    print(f"     {Style.GREEN}[OK]{Style.RESET} Mod directory clean.\n")

    # Stage 2: Download
    log_step("2/3", "Downloading latest mod package...")
    patch_zip = Path(tempfile.gettempdir()) / f"gr_patch_{os.urandom(4).hex()}.zip"
    download_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/{BRANCH}/patch.zip"

    local_patch = Path(__file__).resolve().parent / "patch.zip"
    if local_patch.is_file() and not (Path(__file__).resolve().parent / ".git").is_dir():
        shutil.copy2(local_patch, patch_zip)
        print(f"     {Style.GREEN}[OK]{Style.RESET} Using local patch archive.")
    else:
        try:
            download_with_progress(download_url, patch_zip)
            print(f"     {Style.GREEN}[OK]{Style.RESET} Download complete.\n")
        except Exception as e:
            log_error(f"Failed to download patch.zip from GitHub: {e}")
            input("\nPress Enter to exit...")
            sys.exit(1)

    # Stage 3: Extraction
    check_game_running()
    log_step("3/3", "Extracting mod files to game directory...")
    try:
        with zipfile.ZipFile(patch_zip, "r") as z:
            z.extractall(game_dir)
        print(f"     {Style.GREEN}[OK]{Style.RESET} All mod files successfully synchronized!\n")
    except Exception as e:
        log_error(f"Failed to extract patch archive: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    finally:
        if patch_zip.is_file():
            patch_zip.unlink(missing_ok=True)

    log_success("Grain Rot is now fully modded!")
    print(f"Lobby limit has been raised to {Style.BOLD}12 players{Style.RESET} (configurable up to 16 in")
    print(f"\033[90mHelden/Binaries/Win64/Mods/Konologic-GrainRotTogether/config.ini\033[0m).\n")

    launch = input(f"Press {Style.BOLD}[ENTER]{Style.RESET} to launch Grain Rot now, or close this window to exit: ").strip()
    exe_path = game_dir / "Helden.exe"
    if not exe_path.is_file():
        exe_path = game_dir / "Helden" / "Binaries" / "Win64" / "Helden-Win64-Shipping.exe"

    if exe_path.is_file():
        subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))

if __name__ == "__main__":
    main()

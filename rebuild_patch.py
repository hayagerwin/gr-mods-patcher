import os
import glob
import zipfile
import shutil
import datetime
import re

game_root = r"c:\Games\Grain Rot"
patcher_dir = r"C:\Reedsoft\GrainRotModsPatcher"
zip_path = os.path.join(patcher_dir, "patch.zip")
r2_profile = os.path.expandvars(r"%APPDATA%\r2modmanPlus-local\GrainRot\profiles\Default")

binaries_dir = os.path.join(game_root, "Helden", "Binaries", "Win64")
mods_dir = os.path.join(binaries_dir, "Mods")
signatures_dir = os.path.join(binaries_dir, "UE4SS_Signatures")

print("=== [GrainRotModsPatcher] Mod Sync & Patch Packager ===")

os.makedirs(binaries_dir, exist_ok=True)
os.makedirs(mods_dir, exist_ok=True)
os.makedirs(signatures_dir, exist_ok=True)

# 1. Sync from r2modman profile to game root if r2modman profile exists
if os.path.isdir(r2_profile):
    print(f"[+] Found r2modman profile at: {r2_profile}")
    
    # Core UE4SS files
    for item in ["dwmapi.dll", "ue4ss.dll", "UE4SS-settings.ini"]:
        src = os.path.join(r2_profile, item)
        if os.path.isfile(src):
            dst = os.path.join(binaries_dir, item)
            shutil.copy2(src, dst)
            print(f"  [>] Synced core: {item} -> Helden/Binaries/Win64/{item}")
            
    # Signatures
    r2_sig = os.path.join(r2_profile, "shimloader", "overlay", "Thunderstore-GrainRot_UE4SS", "UE4SS_Signatures")
    if os.path.isdir(r2_sig):
        for f in os.listdir(r2_sig):
            src = os.path.join(r2_sig, f)
            if os.path.isfile(src):
                dst = os.path.join(signatures_dir, f)
                shutil.copy2(src, dst)
                print(f"  [>] Synced signature: {f} -> Helden/Binaries/Win64/UE4SS_Signatures/{f}")
                
    # Mods
    r2_mods = os.path.join(r2_profile, "shimloader", "mod")
    if os.path.isdir(r2_mods):
        for item in os.listdir(r2_mods):
            src = os.path.join(r2_mods, item)
            dst = os.path.join(mods_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  [>] Synced mod folder: {item} -> Helden/Binaries/Win64/Mods/{item}")
            elif os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"  [>] Synced mod file: {item} -> Helden/Binaries/Win64/Mods/{item}")

# Ensure mods.txt has Konologic-GrainRotTogether enabled
mods_txt_path = os.path.join(mods_dir, "mods.txt")
if os.path.isfile(mods_txt_path):
    with open(mods_txt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "Konologic-GrainRotTogether" not in content and "GrainRotTogether" not in content:
        with open(mods_txt_path, "a", encoding="utf-8") as f:
            f.write("\nKonologic-GrainRotTogether : 1\n")
        print("  [+] Appended 'Konologic-GrainRotTogether : 1' to mods.txt")

# 2. Collect entries to pack from game directory
entries_to_pack = set()

# Core UE4SS binaries
for item in ["dwmapi.dll", "ue4ss.dll", "UE4SS-settings.ini"]:
    p = os.path.join(binaries_dir, item)
    if os.path.isfile(p):
        entries_to_pack.add(f"Helden/Binaries/Win64/{item}")

# UE4SS Signatures
if os.path.isdir(signatures_dir):
    for root, _, files in os.walk(signatures_dir):
        for file_name in files:
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, game_root).replace(os.sep, "/")
            entries_to_pack.add(rel_path)

# Mods folder
if os.path.isdir(mods_dir):
    for root, _, files in os.walk(mods_dir):
        for file_name in files:
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, game_root).replace(os.sep, "/")
            entries_to_pack.add(rel_path)

# Prune any entries that are marked in delete_list.txt
delete_list_path = os.path.join(patcher_dir, "delete_list.txt")
if os.path.isfile(delete_list_path):
    with open(delete_list_path, "r", encoding="utf-8", errors="ignore") as f:
        del_lines = [line.strip().replace("\\", "/") for line in f if line.strip() and not line.startswith("#")]
    for del_item in del_lines:
        entries_to_pack = {e for e in entries_to_pack if not (e == del_item or e.startswith(del_item + "/"))}

# 3. Rebuild patch.zip
sorted_entries = sorted(list(entries_to_pack))
backup_zip = zip_path + ".bak"
if os.path.isfile(zip_path):
    shutil.copy2(zip_path, backup_zip)

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for entry in sorted_entries:
        disk_path = os.path.join(game_root, entry.replace("/", os.sep))
        if os.path.isfile(disk_path):
            z.write(disk_path, arcname=entry)
            print(f"Packed from disk: {entry}")
        elif os.path.isfile(backup_zip):
            with zipfile.ZipFile(backup_zip, "r") as zb:
                if entry in zb.namelist():
                    z.writestr(entry, zb.read(entry))
                    print(f"Preserved from backup: {entry}")

if os.path.isfile(backup_zip):
    os.remove(backup_zip)

print(f"[+] Total entries packed: {len(sorted_entries)}")
print(f"[+] patch.zip rebuilt successfully at: {zip_path}")

# 4. Generate patch_info.txt
info_path = os.path.join(patcher_dir, "patch_info.txt")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(info_path, "w", encoding="utf-8") as f:
    f.write(f"Grain Rot Mod Patch Info\n")
    f.write(f"Generated: {now_str}\n")
    f.write(f"Total files: {len(sorted_entries)}\n\n")
    f.write("Files included in patch.zip:\n")
    f.write("=" * 60 + "\n")
    for entry in sorted_entries:
        f.write(f" - {entry}\n")
print(f"[+] Generated patch_info.txt")

# 5. Automatically bump patcher script build timestamp for seamless self-updates
new_build_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

bat_path = os.path.join(patcher_dir, "grain_rot_patcher.bat")
if os.path.isfile(bat_path):
    with open(bat_path, "r", encoding="utf-8", errors="ignore") as f:
        bat_code = f.read()
    bat_code = re.sub(r'set "PATCHER_VERSION=[0-9]+"', f'set "PATCHER_VERSION={new_build_id}"', bat_code)
    with open(bat_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(bat_code)
    print(f"[+] Bumped grain_rot_patcher.bat PATCHER_VERSION -> {new_build_id}")

py_path = os.path.join(patcher_dir, "grain_rot_patcher.py")
if os.path.isfile(py_path):
    with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
        py_code = f.read()
    py_code = re.sub(r'PATCHER_VERSION = "[0-9]+"', f'PATCHER_VERSION = "{new_build_id}"', py_code)
    with open(py_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(py_code)
    print(f"[+] Bumped grain_rot_patcher.py PATCHER_VERSION -> {new_build_id}")

# Copy patcher bat into game root for easy local launching
if os.path.isfile(bat_path):
    shutil.copy2(bat_path, os.path.join(game_root, "grain_rot_patcher.bat"))
    print(f"[+] Synced grain_rot_patcher.bat to game root: {game_root}")

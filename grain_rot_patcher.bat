@echo off
setlocal EnableDelayedExpansion
title Grain Rot Mod Patcher

REM ============================================================================
REM REPOSITORY CONFIGURATION
REM Set your GitHub username, repository name, and branch below.
REM ============================================================================
set "REPO_USER=hayagerwin"
set "REPO_NAME=grain-rot-mods-patcher"
set "BRANCH=main"
set "PATCHER_VERSION=20260901092247"

REM Script directory and config path
set "SCRIPT_DIR=%~dp0"
set "CONFIG_DIR=%LOCALAPPDATA%\GrainRotModsPatcher"
set "CONFIG_FILE=%CONFIG_DIR%\game_path.txt"

REM Initialize ANSI color codes
for /f %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"
set "C_GREEN=%ESC%[92m"
set "C_RED=%ESC%[91m"
set "C_CYAN=%ESC%[96m"
set "C_YELLOW=%ESC%[93m"
set "C_WHITE=%ESC%[97m"
set "C_GRAY=%ESC%[90m"
set "C_BOLD=%ESC%[1m"
set "C_RESET=%ESC%[0m"

echo %C_CYAN%============================================================================
echo                         Grain Rot Mod Patcher
echo ============================================================================%C_RESET%
echo.

set "COMMIT_REF=%BRANCH%"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "try { (Invoke-RestMethod -Uri 'https://api.github.com/repos/%REPO_USER%/%REPO_NAME%/commits/%BRANCH%' -Headers @{'User-Agent'='GrainRot-Mods-Patcher'} -TimeoutSec 3).sha } catch {}" 2^>nul`) do (
    if not "%%S"=="" set "COMMIT_REF=%%S"
)

REM ----------------------------------------------------------------------------
REM 0. SELF-UPDATE CHECK (Always executed FIRST before directory detection)
REM ----------------------------------------------------------------------------
if not defined _GR_PATCHER_SELF_UPDATED (
    REM Don't overwrite if running inside git repo working directory
    if not exist "%SCRIPT_DIR%.git" (
        echo %C_CYAN%[1/2]%C_RESET% Checking for patcher script updates on GitHub...
        set "SCRIPT_URL=https://raw.githubusercontent.com/%REPO_USER%/%REPO_NAME%/!COMMIT_REF!/grain_rot_patcher.bat"
        set "TEMP_SCRIPT=%TEMP%\gr_patcher_update_%RANDOM%.bat"

        curl.exe -s -m 5 -L -f -H "Cache-Control: no-cache" -H "Pragma: no-cache" "!SCRIPT_URL!" -o "!TEMP_SCRIPT!" 2>nul
        if not exist "!TEMP_SCRIPT!" (
            curl.exe -s -m 5 -L -f -H "Cache-Control: no-cache" -H "Pragma: no-cache" "https://raw.githubusercontent.com/%REPO_USER%/%REPO_NAME%/%BRANCH%/grain_rot_patcher.bat?t=%RANDOM%%RANDOM%" -o "!TEMP_SCRIPT!" 2>nul
        )
        if exist "!TEMP_SCRIPT!" (
            set "REMOTE_VERSION="
            for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$txt = Get-Content '!TEMP_SCRIPT!'; foreach($l in $txt){ if($l -match 'PATCHER_VERSION=([0-9a-zA-Z_\.\-]+)') { Write-Output $matches[1]; break } }"`) do (
                set "REMOTE_VERSION=%%V"
            )
            if defined REMOTE_VERSION (
                set "NEEDS_UPDATE=0"
                for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "if ('!REMOTE_VERSION!' -ne '!PATCHER_VERSION!') { Write-Output '1' } else { Write-Output '0' }"`) do (
                    set "NEEDS_UPDATE=%%U"
                )
                if "!NEEDS_UPDATE!"=="1" (
                    echo      %C_YELLOW%[UPDATE AVAILABLE]%C_RESET% Found newer build !REMOTE_VERSION! ^(Current: !PATCHER_VERSION!^)
                    echo      %C_CYAN%[+] Upgrading patcher script...%C_RESET%
                    set "SPAWNER=%TEMP%\gr_updater_%RANDOM%.bat"
                    (
                        echo @echo off
                        echo timeout /t 1 /nobreak ^>nul
                        echo move /y "!TEMP_SCRIPT!" "%~f0" ^>nul
                        echo set "_GR_PATCHER_SELF_UPDATED=1"
                        echo set "_GR_PREV_VERSION=!PATCHER_VERSION!"
                        echo start "" cmd.exe /c "%~f0" %*
                        echo del "%%~f0" ^& exit
                    ) > "!SPAWNER!"
                    start "" cmd.exe /c "!SPAWNER!"
                    exit /b 0
                ) else (
                    echo      %C_GREEN%[UP TO DATE]%C_RESET% Running latest build !PATCHER_VERSION! ^(No update needed^)
                    set "PATCHER_STATUS_TEXT=%C_GREEN%[UP TO DATE] (Build !PATCHER_VERSION! - Synced with GitHub)%C_RESET%"
                )
            ) else (
                echo      %C_GREEN%[UP TO DATE]%C_RESET% Running build !PATCHER_VERSION!
                set "PATCHER_STATUS_TEXT=%C_GREEN%[UP TO DATE] (Build !PATCHER_VERSION!)%C_RESET%"
            )
            del /f /q "!TEMP_SCRIPT!" 2>nul
        ) else (
            echo      %C_GRAY%[OFFLINE / LOCAL]%C_RESET% Running local build !PATCHER_VERSION!
            set "PATCHER_STATUS_TEXT=%C_GRAY%[OFFLINE / LOCAL] (Build !PATCHER_VERSION!)%C_RESET%"
        )
        echo.
    ) else (
        set "PATCHER_STATUS_TEXT=%C_CYAN%[DEV MODE] (Build !PATCHER_VERSION! - Git Working Copy)%C_RESET%"
    )
) else (
    if defined _GR_PREV_VERSION (
        set "PATCHER_STATUS_TEXT=%C_GREEN%[JUST UPDATED] (Successfully upgraded from Build !_GR_PREV_VERSION! -> !PATCHER_VERSION!)%C_RESET%"
    ) else (
        set "PATCHER_STATUS_TEXT=%C_GREEN%[JUST UPDATED] (Successfully updated to Build !PATCHER_VERSION! from GitHub)%C_RESET%"
    )
)

REM ----------------------------------------------------------------------------
REM 1. GAME DIRECTORY DETECTION (Online-Fix, Steam, Custom folders)
REM ----------------------------------------------------------------------------
set "GAME_DIR="

REM Helper function check: Is this a valid Grain Rot folder?
REM Valid if Helden.exe or Helden\Binaries\Win64\Helden-Win64-Shipping.exe exists.

REM Case 1: In-Place Execution (Script is placed directly inside game directory)
if exist "%SCRIPT_DIR%Helden.exe" (
    set "GAME_DIR=%SCRIPT_DIR%"
    goto :game_dir_confirmed
)
if exist "%SCRIPT_DIR%Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
    set "GAME_DIR=%SCRIPT_DIR%"
    goto :game_dir_confirmed
)

REM Case 2: External Execution - Scan for available Grain Rot installations
set "COUNT=0"

REM Scan Saved Location
if exist "%CONFIG_FILE%" (
    set /p SAVED_P=<"%CONFIG_FILE%"
    if defined SAVED_P (
        set "SAVED_P=!SAVED_P:"=!"
        if exist "!SAVED_P!\Helden.exe" (
            set "FOUND_DIR_!SAVED_P!=1"
            set /a COUNT+=1
            for %%K in (!COUNT!) do (
                set "CANDIDATE_%%K=!SAVED_P!"
                set "LABEL_%%K=Saved Location"
            )
        ) else if exist "!SAVED_P!\Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
            set "FOUND_DIR_!SAVED_P!=1"
            set /a COUNT+=1
            for %%K in (!COUNT!) do (
                set "CANDIDATE_%%K=!SAVED_P!"
                set "LABEL_%%K=Saved Location"
            )
        )
    )
)

REM Scan Common Paths and Drives
for %%V in (C D E F G H) do (
    if exist "%%V:\" (
        for %%P in (
            "%%V:\Games\Grain Rot"
            "%%V:\Games\GrainRot"
            "%%V:\SteamLibrary\steamapps\common\Grain Rot"
            "%%V:\Steam\steamapps\common\Grain Rot"
            "%%V:\Program Files (x86)\Steam\steamapps\common\Grain Rot"
            "%%V:\Program Files\Steam\steamapps\common\Grain Rot"
        ) do (
            if exist "%%~P\Helden.exe" (
                if not defined FOUND_DIR_%%~P (
                    set "FOUND_DIR_%%~P=1"
                    set /a COUNT+=1
                    for %%K in (!COUNT!) do (
                        set "CANDIDATE_%%K=%%~P"
                        set "LABEL_%%K=Installed Path"
                    )
                )
            ) else if exist "%%~P\Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
                if not defined FOUND_DIR_%%~P (
                    set "FOUND_DIR_%%~P=1"
                    set /a COUNT+=1
                    for %%K in (!COUNT!) do (
                        set "CANDIDATE_%%K=%%~P"
                        set "LABEL_%%K=Installed Path"
                    )
                )
            )
        )
        if exist "%%V:\Games\" (
            for /d %%D in ("%%V:\Games\*Grain*" "%%V:\Games\Grain*") do (
                if exist "%%~fD\Helden.exe" (
                    if not defined FOUND_DIR_%%~fD (
                        set "FOUND_DIR_%%~fD=1"
                        set /a COUNT+=1
                        for %%K in (!COUNT!) do (
                            set "CANDIDATE_%%K=%%~fD"
                            set "LABEL_%%K=Found on %%V:\Games"
                        )
                    )
                ) else if exist "%%~fD\Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
                    if not defined FOUND_DIR_%%~fD (
                        set "FOUND_DIR_%%~fD=1"
                        set /a COUNT+=1
                        for %%K in (!COUNT!) do (
                            set "CANDIDATE_%%K=%%~fD"
                            set "LABEL_%%K=Found on %%V:\Games"
                        )
                    )
                )
            )
        )
    )
)

REM Scan User Directories (Downloads, Desktop, Documents)
for %%B in ("%USERPROFILE%\Downloads" "%USERPROFILE%\Desktop" "%USERPROFILE%\Documents") do (
    if exist "%%~B\" (
        for /d %%D in ("%%~B\*Grain*" "%%~B\Grain*") do (
            if exist "%%~fD\Helden.exe" (
                if not defined FOUND_DIR_%%~fD (
                    set "FOUND_DIR_%%~fD=1"
                    set /a COUNT+=1
                    for %%K in (!COUNT!) do (
                        set "CANDIDATE_%%K=%%~fD"
                        set "LABEL_%%K=Found in %%~nB"
                    )
                )
            )
            for /d %%S in ("%%~fD\*") do (
                if exist "%%~fS\Helden.exe" (
                    if not defined FOUND_DIR_%%~fS (
                        set "FOUND_DIR_%%~fS=1"
                        set /a COUNT+=1
                        for %%K in (!COUNT!) do (
                            set "CANDIDATE_%%K=%%~fS"
                            set "LABEL_%%K=Found in %%~nB"
                        )
                    )
                )
            )
        )
    )
)

if %COUNT% equ 1 (
    echo %C_CYAN%[2/2]%C_RESET% Auto-detected Grain Rot directory:
    echo      %C_GREEN%!CANDIDATE_1!%C_RESET% %C_GRAY%(!LABEL_1!)%C_RESET%
    echo.
    echo Press %C_WHITE%[ENTER]%C_RESET% to proceed with this folder, or %C_YELLOW%[C]%C_RESET% to choose another:
    set /p "USER_CHOICE=> "
    if /i "!USER_CHOICE!"=="C" (
        goto :manual_picker
    )
    set "GAME_DIR=!CANDIDATE_1!"
    goto :save_and_confirm
)

if %COUNT% gtr 1 (
    echo %C_CYAN%[2/2]%C_RESET% Found multiple Grain Rot installations:
    for /l %%I in (1,1,%COUNT%) do (
        echo      %C_WHITE%[%%I]%C_RESET% !CANDIDATE_%%I! %C_GRAY%(!LABEL_%%I!)%C_RESET%
    )
    echo.
    echo Select an installation %C_WHITE%[1-%COUNT%]%C_RESET% or press %C_YELLOW%[B]%C_RESET% to browse folder:
    set /p "USER_CHOICE=> "
    if /i "!USER_CHOICE!"=="B" (
        goto :manual_picker
    )
    for /l %%I in (1,1,%COUNT%) do (
        if "!USER_CHOICE!"=="%%I" (
            set "GAME_DIR=!CANDIDATE_%%I!"
            goto :save_and_confirm
        )
    )
    set "GAME_DIR=!CANDIDATE_1!"
    goto :save_and_confirm
)

:manual_picker
echo %C_YELLOW%[*] Could not automatically find Grain Rot.%C_RESET%
echo Please drag and drop your Grain Rot game folder here, or press %C_WHITE%[B]%C_RESET% to browse:
set /p "INPUT_PATH=> "
if /i "!INPUT_PATH!"=="B" (
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object Windows.Forms.FolderBrowserDialog; $f.Description = 'Select your Grain Rot game folder'; if($f.ShowDialog() -eq 'OK'){ $f.SelectedPath }" 2^>nul`) do (
        set "INPUT_PATH=%%P"
    )
)

if not defined INPUT_PATH (
    echo %C_RED%[ERROR] No directory selected. Exiting.%C_RESET%
    pause
    exit /b 1
)

set "INPUT_PATH=!INPUT_PATH:"=!"
if exist "!INPUT_PATH!\Helden.exe" (
    set "GAME_DIR=!INPUT_PATH!"
    goto :save_and_confirm
)
if exist "!INPUT_PATH!\Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
    set "GAME_DIR=!INPUT_PATH!"
    goto :save_and_confirm
)

REM Subfolder search
for /d %%S in ("!INPUT_PATH!\*") do (
    if exist "%%~fS\Helden.exe" (
        set "GAME_DIR=%%~fS"
        goto :save_and_confirm
    )
)

echo %C_RED%[ERROR] Helden.exe was not found in: !INPUT_PATH!%C_RESET%
echo Please ensure you selected the root folder of Grain Rot.
pause
exit /b 1

:save_and_confirm
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%" 2>nul
echo !GAME_DIR!>"%CONFIG_FILE%"

:game_dir_confirmed
REM Strip trailing slash if present
if "!GAME_DIR:~-1!"=="\" set "GAME_DIR=!GAME_DIR:~0,-1!"

cls
echo %C_CYAN%============================================================================
echo                         Grain Rot Mod Patcher
echo ============================================================================%C_RESET%
if defined PATCHER_STATUS_TEXT echo !PATCHER_STATUS_TEXT!
echo %C_GRAY%Target Folder:%C_RESET% %C_WHITE%!GAME_DIR!%C_RESET%
echo.

REM ----------------------------------------------------------------------------
REM 2. SYSTEM UTILITIES VERIFICATION
REM ----------------------------------------------------------------------------
where curl.exe >nul 2>nul
if errorlevel 1 (
    echo %C_RED%[ERROR] curl.exe is required but not found in Windows PATH.%C_RESET%
    pause
    exit /b 1
)

where tar.exe >nul 2>nul
if errorlevel 1 (
    echo %C_RED%[ERROR] tar.exe is required but not found in Windows PATH.%C_RESET%
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------------
REM 3. CLEANUP / DELETION STAGE
REM ----------------------------------------------------------------------------
echo %C_CYAN%[1/3]%C_RESET% Checking for outdated mods...
set "TEMP_DELETE_LIST=%TEMP%\gr_delete_list_%RANDOM%.txt"
set "DELETE_URL=https://raw.githubusercontent.com/%REPO_USER%/%REPO_NAME%/!COMMIT_REF!/delete_list.txt"

curl.exe -s -m 5 -L -f -H "Cache-Control: no-cache" -H "Pragma: no-cache" "!DELETE_URL!" -o "!TEMP_DELETE_LIST!" 2>nul
if not exist "!TEMP_DELETE_LIST!" (
    if exist "%SCRIPT_DIR%delete_list.txt" (
        copy /y "%SCRIPT_DIR%delete_list.txt" "!TEMP_DELETE_LIST!" >nul 2>nul
    )
)

if exist "!TEMP_DELETE_LIST!" (
    for /f "usebackq delims=" %%L in ("!TEMP_DELETE_LIST!") do (
        set "DEL_LINE=%%L"
        REM Ignore comment lines
        if not "!DEL_LINE:~0,1!"=="#" (
            set "DEL_TARGET=!GAME_DIR!\!DEL_LINE!"
            if exist "!DEL_TARGET!" (
                if exist "!DEL_TARGET!\*" (
                    rmdir /s /q "!DEL_TARGET!" 2>nul
                    echo      %C_YELLOW%[-] Removed obsolete directory:%C_RESET% !DEL_LINE!
                ) else (
                    del /f /q /a "!DEL_TARGET!" 2>nul
                    echo      %C_YELLOW%[-] Removed obsolete file:%C_RESET% !DEL_LINE!
                )
            )
        )
    )
    del /f /q "!TEMP_DELETE_LIST!" 2>nul
)
echo      %C_GREEN%[OK]%C_RESET% Mod directory clean.
echo.

REM ----------------------------------------------------------------------------
REM 4. DOWNLOAD STAGE
REM ----------------------------------------------------------------------------
echo %C_CYAN%[2/3]%C_RESET% Downloading latest mod patch from GitHub...
set "PATCH_ZIP=%TEMP%\gr_patch_%RANDOM%.zip"
set "DOWNLOAD_URL=https://raw.githubusercontent.com/%REPO_USER%/%REPO_NAME%/!COMMIT_REF!/patch.zip"

REM Check local patch.zip fallback if running from local repo
if exist "%SCRIPT_DIR%patch.zip" if not exist "%SCRIPT_DIR%.git" (
    copy /y "%SCRIPT_DIR%patch.zip" "!PATCH_ZIP!" >nul
    echo      %C_GREEN%[OK]%C_RESET% Using local patch archive.
) else (
    curl.exe -# -L -f -H "Cache-Control: no-cache" -H "Pragma: no-cache" "!DOWNLOAD_URL!" -o "!PATCH_ZIP!"
    if errorlevel 1 (
        echo.
        echo      %C_YELLOW%[*] Retrying primary branch url...%C_RESET%
        curl.exe -# -L -f -H "Cache-Control: no-cache" -H "Pragma: no-cache" "https://raw.githubusercontent.com/%REPO_USER%/%REPO_NAME%/%BRANCH%/patch.zip?t=%RANDOM%" -o "!PATCH_ZIP!"
    )
)

if not exist "!PATCH_ZIP!" (
    echo.
    echo %C_RED%[ERROR] Failed to download patch.zip from GitHub repository:%C_RESET%
    echo %C_WHITE%https://github.com/%REPO_USER%/%REPO_NAME%%C_RESET%
    echo.
    echo Please ensure the repository is public and 'patch.zip' exists on branch '%BRANCH%'.
    pause
    exit /b 1
)

echo      %C_GREEN%[OK]%C_RESET% Mod patch downloaded successfully.
echo.

REM ----------------------------------------------------------------------------
REM 5. EXTRACTION STAGE
REM ----------------------------------------------------------------------------
echo %C_CYAN%[3/3]%C_RESET% Extracting and applying mod files to game...
tar.exe -xf "!PATCH_ZIP!" -C "!GAME_DIR!"
if errorlevel 1 (
    echo %C_RED%[ERROR] Failed to extract mod files.%C_RESET%
    del /f /q "!PATCH_ZIP!" 2>nul
    pause
    exit /b 1
)

del /f /q "!PATCH_ZIP!" 2>nul
echo      %C_GREEN%[OK]%C_RESET% All mod files successfully synchronized!
echo.

REM Copy patcher script to game folder if running externally
if not exist "!GAME_DIR!\grain_rot_patcher.bat" (
    copy /y "%~f0" "!GAME_DIR!\grain_rot_patcher.bat" >nul 2>nul
)

echo %C_GREEN%============================================================================
echo                SUCCESS: Grain Rot is now fully modded!
echo ============================================================================%C_RESET%
echo.
echo Lobby limit has been raised to %C_WHITE%12 players%C_RESET% (configurable up to 16 in 
echo %C_GRAY%Helden\Binaries\Win64\Mods\Konologic-GrainRotTogether\config.ini%C_RESET%).
echo.
echo Press %C_WHITE%[ENTER]%C_RESET% to Launch Grain Rot now, or close this window to exit.
set /p "LAUNCH_CHOICE=> "

if exist "!GAME_DIR!\Helden.exe" (
    cd /d "!GAME_DIR!"
    start "" "!GAME_DIR!\Helden.exe"
) else if exist "!GAME_DIR!\Helden\Binaries\Win64\Helden-Win64-Shipping.exe" (
    cd /d "!GAME_DIR!\Helden\Binaries\Win64"
    start "" "!GAME_DIR!\Helden\Binaries\Win64\Helden-Win64-Shipping.exe"
)

exit /b 0

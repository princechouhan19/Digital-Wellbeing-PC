@echo off
setlocal
echo Building Digital Wellbeing Installer...

set "ISCC1=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC2=C:\Program Files\Inno Setup 6\ISCC.exe"
set "ISCC3=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

set "ISCC_PATH="
if exist "%ISCC1%" set "ISCC_PATH=%ISCC1%"
if exist "%ISCC2%" set "ISCC_PATH=%ISCC2%"
if exist "%ISCC3%" set "ISCC_PATH=%ISCC3%"

if "%ISCC_PATH%"=="" (
    echo Error: Inno Setup 6 Compiler ^(ISCC.exe^) not found.
    echo Please install Inno Setup 6 from https://jrsoftware.org/isdl.php
    exit /b 1
)

:: Get version from version.json using Python
for /f "delims=" %%A in ('python -c "import sys, json; print(json.load(open(sys.argv[1]))['version'])" "%~dp0..\version.json"') do set "APP_VERSION=%%A"
if "%APP_VERSION%"=="" (
    echo Error: Could not read version from version.json
    exit /b 1
)
echo Building version: %APP_VERSION%

"%ISCC_PATH%" /dMyAppVersion="%APP_VERSION%" "%~dp0DigitalWellbeing.iss"
if %errorlevel% neq 0 (
    echo Failed to build installer.
    exit /b %errorlevel%
)

echo Installer built successfully!

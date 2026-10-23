# Digital Wellbeing Installer

This folder contains the permanent Inno Setup installer script for **Digital Wellbeing**. The source file is kept here separately from the generated executable for easy maintenance across future releases.

## Folder Structure
- `DigitalWellbeing.iss`: The primary Inno Setup script containing all configuration parameters (paths, metadata, icons).
- `build_installer.bat`: A helper script that automatically detects your Inno Setup installation and triggers the compiler.

## Prerequisites
To generate a new installer, you must have the **Inno Setup 6 Compiler** installed.
You can download it for free from: [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)

## How to Build a New Release

When you are ready to ship a new version of the application, follow these exact steps:

### 1. Update Version Number
Update the version string in the `version.json` file in the project root.
That's it! This is your single source of truth.

### 2. Run the Build Script
Run the automated build script from the project root:
```bash
python build.py
```
This script will automatically:
1. Update `file_version_info.txt` with the new version properties.
2. Bundle the application into `dist/DigitalWellbeing/` via PyInstaller.
3. Automatically code-sign the built executable (if configured).
4. Automatically execute the `build_installer.bat` compiler script.
5. Automatically code-sign the final installer (if configured).

The final installer (`DigitalWellbeingSetup.exe`) will be output to the `dist/` directory at the root of the project.

## Code Signing
The build pipeline natively supports Microsoft Authenticode signing via `signtool.exe`. 
To enable automatic code signing:
1. Place your certificate file named `cert.pfx` in the root of the project.
2. Set your certificate password (if any) as an environment variable named `SIGN_PASSWORD`.
3. Ensure the Windows SDK is installed (it will auto-detect `signtool.exe` from `C:\Program Files (x86)\Windows Kits\10\bin\...\x64`).

If `cert.pfx` is missing, the build pipeline will safely skip code signing and continue normally without failing.

## Troubleshooting

- **"ISCC.exe not found"**: Ensure you have downloaded and installed Inno Setup 6. If you installed it to a custom directory, update the paths inside `build_installer.bat`.
- **"Source file not found"**: Ensure you have successfully run the PyInstaller build step. The Inno Setup script expects `dist\DigitalWellbeing\*` to exist.
- **"File in Use"**: If the installer fails to copy files, ensure the application is completely closed before building or installing over it.

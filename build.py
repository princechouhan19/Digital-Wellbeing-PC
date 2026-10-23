import json
import os
import re
import subprocess
import sys
import glob
from pathlib import Path

def get_version():
    with open("version.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["version"]

def update_file_version_info(version_str):
    print(f"Updating file_version_info.txt to version {version_str}...")
    
    # Parse version (e.g., "2.0.1" -> (2, 0, 1, 0))
    parts = version_str.split(".")
    while len(parts) < 4:
        parts.append("0")
    tuple_str = f"({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})"
    
    path = "file_version_info.txt"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Replace filevers and prodvers tuples
    content = re.sub(r"filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)", f"filevers={tuple_str}", content)
    content = re.sub(r"prodvers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)", f"prodvers={tuple_str}", content)
    
    # Replace FileVersion and ProductVersion string structs
    content = re.sub(
        r"StringStruct\('FileVersion',\s*'[^']+'\)",
        f"StringStruct('FileVersion', '{version_str}')",
        content
    )
    content = re.sub(
        r"StringStruct\('ProductVersion',\s*'[^']+'\)",
        f"StringStruct('ProductVersion', '{version_str}')",
        content
    )
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Done updating file_version_info.txt.")

def update_manifest_version(version_str):
    """
    Update app.manifest assemblyIdentity version to match version_str.
    The manifest expects a four-part version (major.minor.patch.build).
    """
    manifest_path = Path("app.manifest")
    if not manifest_path.exists():
        print("app.manifest not found; skipping manifest update.")
        return
    # Ensure a four-part version
    parts = version_str.split(".")
    while len(parts) < 4:
        parts.append("0")
    manifest_ver = f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}"
    content = manifest_path.read_text(encoding="utf-8")
    def _repl(m):
        return m.group(1) + manifest_ver + m.group(3)
    new_content = re.sub(r'(assemblyIdentity[^>]+version=")([^"]+)("\s?)', _repl, content)
    if new_content == content:
        # Try alternate pattern without trailing space (fallback)
        new_content = re.sub(r'(assemblyIdentity[^>]+version=")([^"]+)(")', _repl, content)
    manifest_path.write_text(new_content, encoding="utf-8")
    print(f"Updated app.manifest to version {manifest_ver}")


def get_signtool():
    paths = glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.*\x64\signtool.exe")
    if paths:
        # Sort to get the highest version
        return sorted(paths)[-1]
    return None

def sign_file(file_path):
    cert_path = "cert.pfx"
    if not os.path.exists(cert_path):
        print(f"Skipping code signing for {file_path} (cert.pfx not found).")
        return
    
    signtool = get_signtool()
    if not signtool:
        print(f"Skipping code signing for {file_path} (signtool.exe not found in Windows Kits).")
        return
        
    password = os.environ.get("SIGN_PASSWORD", "")
    print(f"Signing {file_path}...")
    cmd = [
        signtool, "sign", "/f", cert_path, "/fd", "SHA256", 
        "/tr", "http://timestamp.digicert.com", "/td", "SHA256"
    ]
    if password:
        cmd.extend(["/p", password])
    cmd.append(str(file_path))
    
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"Warning: Failed to sign {file_path}.")
    else:
        print(f"Successfully signed {file_path}.")

def run_pyinstaller():
    print("Running PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", "digital_wellbeing.spec", "--clean", "--noconfirm"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("PyInstaller failed!")
        sys.exit(result.returncode)

def run_inno_setup():
    print("Running Inno Setup compiler...")
    bat_path = Path("installer") / "build_installer.bat"
    if not bat_path.exists():
        print("Warning: build_installer.bat not found. Skipping Inno Setup.")
        return False
    # Execute the batch file using cmd
    result = subprocess.run(["cmd", "/c", str(bat_path)])
    if result.returncode != 0:
        print("Warning: Inno Setup failed or ISCC.exe is not installed on this system.")
        print("Skipping installer setup compilation. Portable release will still be packaged.")
        return False
    return True

def run_custom_installer(version_str):
    print("Building custom installer wizard with PyInstaller...")
    ps1_path = Path("installer") / "build_installer.ps1"
    if not ps1_path.exists():
        print("Warning: installer/build_installer.ps1 not found. Skipping custom installer.")
        return False
    # Ensure assets directory is present in dist
    dist_dir = Path("dist") / "DigitalWellbeing"
    if dist_dir.exists() and Path("assets").is_dir():
        import shutil
        try:
            shutil.copytree("assets", dist_dir / "assets", dirs_exist_ok=True)
        except Exception:
            pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_path)]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        setup_exe = Path("dist") / "Digital Wellbeing Setup.exe"
        if setup_exe.exists():
            sign_file(setup_exe)
            print(f"Custom installer wizard successfully built at {setup_exe}")
            return True
    print("Warning: Custom installer wizard build failed.")
    return False

def package_zip(version_str):
    dist_dir = Path("dist") / "DigitalWellbeing"
    output_zip = Path("dist") / f"DigitalWellbeing-v{version_str}.zip"
    latest_zip = Path("dist") / "DigitalWellbeing.zip"
    if not dist_dir.exists() or not (dist_dir / "DigitalWellbeing.exe").exists():
        print("Warning: dist/DigitalWellbeing/DigitalWellbeing.exe not found. Cannot create zip.")
        return
    print(f"Creating release archive at {output_zip}...")
    import zipfile
    import shutil
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(dist_dir.parent))
    try:
        shutil.copyfile(output_zip, latest_zip)
    except Exception as exc:
        print(f"Warning copying to latest zip: {exc}")
    print(f"Release archives created successfully at {output_zip} and {latest_zip}.")

if __name__ == "__main__":
    v = get_version()
    print(f"--- Starting Release Build for v{v} ---")
    update_file_version_info(v)
    update_manifest_version(v)
    run_pyinstaller()
    # Ensure assets directory is present directly in dist folder alongside _internal
    dist_dir = Path("dist") / "DigitalWellbeing"
    if dist_dir.exists():
        import shutil
        dest_assets = dist_dir / "assets"
        try:
            shutil.copytree("assets", dest_assets, dirs_exist_ok=True)
            print("Copied assets to dist/DigitalWellbeing/assets")
        except Exception as e:
            print(f"Warning copying assets to dist: {e}")
    sign_file(Path("dist") / "DigitalWellbeing" / "DigitalWellbeing.exe")
    inno_success = run_inno_setup()
    if inno_success:
        # Rename generated installer to include version for updater discoverability
        inno_out = Path("dist") / "DigitalWellbeingSetup.exe"
        if inno_out.exists():
            dest_name = Path(f"DigitalWellbeingSetup-{v}.exe")
            dest_path = Path("dist") / dest_name
            try:
                inno_out.replace(dest_path)
                print(f"Renamed installer to {dest_path}")
                sign_file(dest_path)
            except Exception as exc:
                print(f"Warning: Failed to rename/sign installer: {exc}")
                # fallback to signing original
                sign_file(inno_out)
        else:
            print("Warning: Inno Setup did not produce expected installer 'DigitalWellbeingSetup.exe'. Skipping rename.")
    else:
        print("Inno Setup step skipped or not installed. Building custom installer wizard.")
        run_custom_installer(v)
    package_zip(v)
    print(f"--- Successfully built release v{v} ---")

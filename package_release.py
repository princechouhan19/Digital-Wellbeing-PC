# Helper script to package Digital Wellbeing release assets
import os
import zipfile
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).parent
    dist_dir = root / "dist" / "DigitalWellbeing"
    output_zip = root / "dist" / "DigitalWellbeing.zip"
    iss_file = root / "installer" / "DigitalWellbeing.iss"
    
    if not dist_dir.exists() or not (dist_dir / "DigitalWellbeing.exe").exists():
        print("[ERROR] dist/DigitalWellbeing/DigitalWellbeing.exe not found. Run PyInstaller first!")
        return

    print("[INFO] Zipping distribution folder...")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(dist_dir.parent))
    print(f"[SUCCESS] Zipped release created at {output_zip}")

    # Check for Inno Setup Compiler (ISCC.exe)
    iscc_paths = [
        "iscc.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    
    iscc_found = None
    for p in iscc_paths:
        try:
            if p == "iscc.exe":
                subprocess.run(["iscc", "/?"], capture_output=True)
                iscc_found = "iscc"
                break
            elif Path(p).exists():
                iscc_found = p
                break
        except Exception:
            continue
            
    if iscc_found:
        print(f"[INFO] Compiling installer using {iscc_found}...")
        try:
            res = subprocess.run([iscc_found, str(iss_file)], capture_output=True, text=True)
            if res.returncode == 0:
                print("[SUCCESS] Installer setup compiled at dist/DigitalWellbeingSetup.exe")
            else:
                print(f"[ERROR] Installer compilation failed:\n{res.stderr}\n{res.stdout}")
        except Exception as exc:
            print(f"[ERROR] Compilation run failed: {exc}")
    else:
        print("[WARNING] Inno Setup compiler (ISCC.exe) not found in PATH or Program Files.")
        print("[INFO] To build the Windows installer (.exe):")
        print("  1. Download and install Inno Setup 6 (https://jrsoftware.org/isdl.php)")
        print("  2. Open installer.iss in Inno Setup and click 'Compile', or run:")
        print(r'     & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss')

if __name__ == "__main__":
    main()

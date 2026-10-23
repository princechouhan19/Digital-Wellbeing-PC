import os, subprocess
from pathlib import Path

t = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Digital Wellbeing'
EXE = 'DigitalWellbeing.exe'
dest = Path(os.environ.get('APPDATA', '')) / 'Microsoft/Windows/Start Menu/Programs' / 'Digital Wellbeing.lnk'
dest.parent.mkdir(parents=True, exist_ok=True)

cmd = (
    '$ws=New-Object -ComObject WScript.Shell;'
    f"$s=$ws.CreateShortcut('{dest}');$s.TargetPath='{t / EXE}';"
    f"$s.WorkingDirectory='{t}';$s.IconLocation='{t / EXE},0';$s.Save()"
)
print('Running:', cmd)
res = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True)
print('Exit code:', res.returncode)
print('Stdout:', res.stdout)
print('Stderr:', res.stderr)
print('Dest exists:', dest.exists())

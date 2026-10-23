from pathlib import Path
import subprocess
import time
import ctypes
import os
import sys

exe = Path(__file__).parent.parent / 'dist' / 'DigitalWellbeing' / 'DigitalWellbeing.exe'
if not exe.exists():
    print('EXE not found:', exe)
    sys.exit(2)
print('Launching', exe)
proc = subprocess.Popen([str(exe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# wait for window to appear
time.sleep(2)
# attempt to close debug msgbox if present
user32 = ctypes.windll.user32
FindWindowW = user32.FindWindowW
SendMessageW = user32.SendMessageW
WM_CLOSE = 0x0010
try:
    hwnd = FindWindowW(None, 'SleepGuard Debug')
    if hwnd:
        print('Found debug dialog hwnd=', hwnd, ' - sending WM_CLOSE')
        SendMessageW(hwnd, WM_CLOSE, 0, 0)
    else:
        print('Debug dialog not found')
except Exception as e:
    print('Error finding/closing dialog:', e)

# allow app to initialize and run its startup tasks
time.sleep(10)
# check DB file
db_path = Path.home() / 'AppData' / 'Local' / 'DigitalWellbeing' / 'digital_wellbeing.db'
print('DB exists?', db_path.exists(), str(db_path))
# check log file
log_path = Path.home() / 'AppData' / 'Local' / 'DigitalWellbeing' / 'digital_wellbeing.log'
print('Log exists?', log_path.exists(), str(log_path))
if log_path.exists():
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.read().splitlines()
        print('\n---- Last 60 log lines ----')
        for l in lines[-60:]:
            print(l)

# terminate process
print('Terminating process...')
proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
print('Process ended. rc=', proc.returncode)

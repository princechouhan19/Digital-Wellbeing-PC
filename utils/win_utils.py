from __future__ import annotations

import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import Optional


def get_app_user_data_dir() -> Path:
    path = Path.home() / "AppData" / "Local" / "DigitalWellbeing"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_windows_version() -> tuple[int, int, int]:
    try:
        ver = ctypes.windll.ntdll.RtlGetVersion
        class RTL_OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", ctypes.c_ulong),
                ("dwMajorVersion", ctypes.c_ulong),
                ("dwMinorVersion", ctypes.c_ulong),
                ("dwBuildNumber", ctypes.c_ulong),
                ("dwPlatformId", ctypes.c_ulong),
                ("szCSDVersion", ctypes.c_wchar * 128),
                ("wServicePackMajor", ctypes.c_ushort),
                ("wServicePackMinor", ctypes.c_ushort),
                ("wSuiteMask", ctypes.c_ushort),
                ("wProductType", ctypes.c_byte),
                ("wReserved", ctypes.c_byte),
            ]
        osvi = RTL_OSVERSIONINFOEXW()
        osvi.dwOSVersionInfoSize = ctypes.sizeof(osvi)
        ctypes.windll.ntdll.RtlGetVersion(ctypes.byref(osvi))
        return (osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber)
    except Exception:
        return (10, 0, 0)


def is_safe_lock_target(exe_path: str, process_name: str) -> bool:
    """
    Security validation: checks if locking this executable is safe.
    Rejects system files, hidden files, OS components, and the app itself.
    """
    if not exe_path or not process_name:
        return False
        
    p_lower = process_name.lower()
    
    if p_lower == "digitalwellbeing.exe":
        return False

    # Must be an executable
    if not p_lower.endswith(".exe"):
        return False

    # Avoid circular import by importing inside
    try:
        from protection.app_locker import SYSTEM_SAFE
        if p_lower in SYSTEM_SAFE:
            return False
    except ImportError:
        pass

    path = Path(exe_path)
    try:
        resolved = path.resolve(strict=False)
        resolved_lower = str(resolved).lower()
        
        import os
        win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
        if resolved_lower.startswith(win_dir):
            return False
            
        prog_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData").lower()
        if resolved_lower.startswith(prog_data):
            return False
            
        if "windowsapps" in resolved_lower:
            # System frameworks / internal components in WindowsApps are blocked,
            # but legitimate 3rd-party user applications (e.g. Spotify, WhatsApp, Netflix) are allowed.
            system_frameworks = (
                "microsoft.windows.", "microsoft.ui.xaml", "microsoft.vclibs",
                "microsoft.net.native", "microsoft.services.store", "windows.immersivecontrolpanel",
                "windows.shellexperiencehost", "microsoft.windowscommunicationsapps",
                "microsoft.system", "microsoft.bing",
                # Windows screenshot and capture utilities (never lockable)
                "microsoft.screensketch", "microsoftwindows.client.",
                # OEM hardware / driver / thermal management packages
                ".hpthermalcontrol", ".hpsystemeventutility", ".hpsupportassistant",
                ".hppencontrol", ".hpenhance", "ad2f1837."
            )
            if any(fw in resolved_lower for fw in system_frameworks):
                return False

        # OEM hardware / driver directories
        oem_dirs = (
            "\\hp\\hp touchpoint analytics",
            "\\hp\\hp system event",
            "\\hp\\hp support framework",
            "\\hp\\hp media network",
        )
        if any(d in resolved_lower for d in oem_dirs):
            return False

        if "common files\\microsoft shared" in resolved_lower:
            return False
            
    except Exception:
        return False
        
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs != -1:
            FILE_ATTRIBUTE_HIDDEN = 0x2
            FILE_ATTRIBUTE_SYSTEM = 0x4
            if (attrs & FILE_ATTRIBUTE_HIDDEN) or (attrs & FILE_ATTRIBUTE_SYSTEM):
                return False
    except Exception:
        pass
        
    return True

def get_session_id(pid: int) -> int:
    """Gets the terminal services session ID for the given PID."""
    sid = ctypes.c_ulong()
    try:
        if ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid)):
            return sid.value
    except Exception:
        pass
    return -1

def get_executable_product_name(exe_path: str) -> str:
    """Attempts to extract the ProductName or FileDescription from the PE version info."""
    try:
        import win32api
        
        info = win32api.GetFileVersionInfo(exe_path, "\\")
        if not info:
            return ""
            
        try:
            lang, codepage = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')[0]
        except Exception:
            return ""
            
        str_info = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, "ProductName")
        try:
            prod = win32api.GetFileVersionInfo(exe_path, str_info)
            if prod:
                return prod
        except Exception:
            pass
            
        str_info = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, "FileDescription")
        desc = win32api.GetFileVersionInfo(exe_path, str_info)
        return desc if desc else ""
    except Exception:
        return ""

SHELL_AND_SERVICE_PROCESSES: frozenset[str] = frozenset({
    "explorer.exe", "services.exe", "svchost.exe", "wininit.exe",
    "smss.exe", "csrss.exe", "winlogon.exe", "sihost.exe", "userinit.exe"
})


def resolve_root_application(proc) -> tuple[Optional[object], str]:
    """
    Resolves the root application process and executable name for a given process
    by climbing its ancestor tree up to the desktop shell or system service manager.
    Returns (root_process, root_name_lowercase).
    """
    if proc is None:
        return None, ""
    try:
        parents_fn = getattr(proc, "parents", None)
        if not callable(parents_fn):
            name = getattr(proc, "name", lambda: "")()
            return proc, name.lower() if isinstance(name, str) else ""

        parents = proc.parents()
        if not parents or not isinstance(parents, (list, tuple)):
            name = proc.name()
            return proc, name.lower() if isinstance(name, str) else ""

        for i, p in enumerate(parents):
            try:
                p_name = p.name()
                if isinstance(p_name, str) and p_name.lower() in SHELL_AND_SERVICE_PROCESSES:
                    if i > 0:
                        root = parents[i - 1]
                    else:
                        root = proc
                    r_name = root.name()
                    return root, r_name.lower() if isinstance(r_name, str) else ""
            except Exception:
                pass

        root = parents[-1]
        r_name = root.name()
        return root, r_name.lower() if isinstance(r_name, str) else ""
    except Exception:
        try:
            name = proc.name()
            return proc, name.lower() if isinstance(name, str) else ""
        except Exception:
            return proc, ""


def get_visible_window_pids() -> set[int]:
    """
    Enumerates processes that own visible, interactive, non-cloaked desktop windows.
    Filters out invisible windows, 0x0 tooltips, offscreen stubs, and cloaked frames.
    """
    pids: set[int] = set()
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        def enum_window_callback(hwnd, _):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True

                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True

                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if (rect.right - rect.left) < 20 or (rect.bottom - rect.top) < 20:
                    return True

                cloaked = ctypes.c_int(0)
                DWMWA_CLOAKED = 14
                dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value != 0:
                    return True

                wpid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
                if wpid.value > 4:
                    pids.add(wpid.value)
            except Exception:
                pass
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        cb = WNDENUMPROC(enum_window_callback)
        user32.EnumWindows(cb, 0)

        if not pids:
            try:
                hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
                if hdesk:
                    user32.EnumDesktopWindows(hdesk, cb, 0)
                    user32.CloseDesktop(hdesk)
            except Exception:
                pass
    except Exception as exc:
        try:
            from core.logger import logger
            logger.debug(f"[WINDOW] Failed to enumerate visible window PIDs: {exc}")
        except Exception:
            pass

    return pids


def is_user_facing_application(
    pid: Optional[int],
    exe_path: str,
    process_name: str,
    visible_pids: Optional[set] = None,
    display_name: str = "",
) -> bool:
    """
    Discovery classification: checks if a process is a legitimate user application 
    that should be presented in the Running Processes UI list or targeted by Focus Mode.
    """
    if not is_safe_lock_target(exe_path, process_name):
        return False
        
    if pid is not None:
        if get_session_id(pid) == 0:
            return False

    p_lower = process_name.lower()

    # Explicit OS / Infrastructure background blocklist
    infrastructure = {
        "svchost.exe", "conhost.exe", "dllhost.exe", "cmd.exe", 
        "powershell.exe", "sihost.exe", "taskhostw.exe", "ctfmon.exe", 
        "explorer.exe", "searchapp.exe", "startmenuexperiencehost.exe",
        "runtimebroker.exe", "applicationframehost.exe", "securityhealthsystray.exe",
        "systemsettings.exe", "wmiprvse.exe", "spoolsv.exe", "lsass.exe", 
        "csrss.exe", "smss.exe", "wininit.exe", "winlogon.exe", "services.exe",
        "fontdrvhost.exe", "dwm.exe", "textinputhost.exe", "audiodg.exe",
        "smartscreen.exe", "wudfhost.exe", "wmiapsrv.exe", "winrshost.exe",
        "backgroundtaskhost.exe", "backgroundtransferhost.exe",
        "dashost.exe", "sppsvc.exe", "wscsvc.exe", "wuauserv.exe",
        "searchhost.exe", "shellexperiencehost.exe", "lockapp.exe",
        # Windows screenshot utilities are protected system tools, never blockable distraction apps
        "snippingtool.exe", "screenclippinghost.exe"
    }
    if p_lower in infrastructure:
        return False

    # Language server and developer infrastructure keywords in executable name
    lsp_indicators = (
        "languageserver", "language_server", "pyrefly", "pyright", "rust-analyzer",
        "clangd", "gopls", "vtsls", "omnisharp", "tsserver", "jdtls", "solargraph", "zls"
    )
    if any(kw in p_lower for kw in lsp_indicators):
        return False

    # Check Process Command Line & Parent Process Relationships (if PID available)
    if pid is not None:
        try:
            import psutil
            proc_obj = psutil.Process(pid)
            try:
                cmdline = proc_obj.cmdline()
                # Reject DCOM / COM / WinRT background servers and OS-invoked background triggers
                if any(
                    arg.lower().startswith((
                        "-servername:", "/servername:", "-embedding", "/embedding",
                        "/invokerpraid:", "-invokerpraid:", "--type="
                    )) or arg.lower() in (
                        "launchedbybglauncher", "-background", "/background",
                        "--enable_lsp", "--lsp", "lsp"
                    ) or "chrome-devtools-mcp" in arg.lower() or "mcp-server" in arg.lower()
                    or "language_server" in arg.lower() or "language-server" in arg.lower()
                    for arg in cmdline
                ):
                    return False
            except Exception:
                pass

            try:
                parent = proc_obj.parent()
                if parent:
                    parent_name = parent.name().lower()
                    # Processes spawned directly by service hosts or system daemons without visible windows
                    if parent_name in ("svchost.exe", "services.exe", "wininit.exe", "smss.exe", "csrss.exe"):
                        if not visible_pids or pid not in visible_pids:
                            return False

                    # Children of IDEs / editors without visible desktop windows are background helpers
                    ide_parents = (
                        "code.exe", "antigravity.exe", "antigravity ide.exe", "devenv.exe",
                        "idea64.exe", "pycharm64.exe", "webstorm64.exe"
                    )
                    if any(ide in parent_name for ide in ide_parents):
                        if not visible_pids or pid not in visible_pids:
                            return False
            except Exception:
                pass
        except Exception:
            pass

    # Window Presence Signal:
    # If visible window PIDs are supplied, an application without a visible desktop window
    # is a background / helper process, NOT an interactive user-facing block target!
    if visible_pids is not None:
        if pid is not None and pid in visible_pids:
            return True
        elif pid is not None:
            return False

    # Check Metadata
    desc_lower = ""
    prod_lower = ""
    company_lower = ""
    if exe_path:
        try:
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, "\\")
            if info:
                lang, codepage = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')[0]
                try:
                    prod = win32api.GetFileVersionInfo(exe_path, u'\\StringFileInfo\\%04X%04X\\ProductName' % (lang, codepage))
                    if prod: prod_lower = prod.lower()
                except Exception: pass
                
                try:
                    desc = win32api.GetFileVersionInfo(exe_path, u'\\StringFileInfo\\%04X%04X\\FileDescription' % (lang, codepage))
                    if desc: desc_lower = desc.lower()
                except Exception: pass

                try:
                    comp = win32api.GetFileVersionInfo(exe_path, u'\\StringFileInfo\\%04X%04X\\CompanyName' % (lang, codepage))
                    if comp: company_lower = comp.lower()
                except Exception: pass
        except Exception:
            pass

    # OEM Hardware & Thermal/Event Driver Filtering
    oem_vendors = ("hp", "hp inc.", "hewlett-packard", "dell", "lenovo", "asus", "asustek", "realtek", "synaptics", "intel")
    if any(v in company_lower for v in oem_vendors):
        hardware_terms = (
            "thermal", "systemevent", "systemmanagement", "systemmanager",
            "touchpoint", "diagnostics", "hardware", "sensor", "energy", "power"
        )
        if any(term in desc_lower or term in prod_lower or term in p_lower for term in hardware_terms):
            if not visible_pids or pid not in visible_pids:
                return False

    # Explicit known helper suffixes (filename)
    blocked_suffixes = [
        "service.exe", "updater.exe", "update.exe", "helper.exe", 
        "crashpad.exe", "crashhandler.exe", "handler.exe", "handler64.exe", 
        "handler32.exe", "broker.exe", "reporter.exe", "daemon.exe", 
        "agent.exe", "installer.exe", "setup.exe", "monitor.exe", 
        "host.exe", "clicktorun.exe", "recovery.exe", "launcher.exe", "migrator.exe",
        "startuptask.exe", "cli.exe", "background.exe", ".bg.exe",
        "autostart.exe", "autostarter.exe", "notifier.exe", "notification.exe",
        "pushnotifications.exe",
    ]
    for suffix in blocked_suffixes:
        if p_lower.endswith(suffix):
            return False

    # Block background/helper keywords in description, product name, or display name
    blocked_keywords = [
        "service", "updater", "helper", "crash", "monitor", "daemon", 
        "broker", "reporter", "background", "proxy", "notification", "tray",
        "autostart", "systemmanagement", "systemmanager", "thermalcontrol",
        "systemevent"
    ]
    disp_lower = display_name.lower() if display_name else ""
    for kw in blocked_keywords:
        if kw in desc_lower or kw in prod_lower or (disp_lower and kw in disp_lower):
            return False

    # Edge cases
    if p_lower in ["jusched.exe", "jucheck.exe", "jqs.exe", "hpcommrecovery.exe", "vgtray.exe", "hpsystemmanagement.exe"]:
        return False
        
    return True


def clean_fallback_name(process_name: str) -> str:
    """
    Cleans raw executable names and package prefixes into friendly display names.
    e.g. 'ad2f1837.hpsupportassistant.exe' -> 'HP Support Assistant'
         'fingersoft.hillclimbracing.exe' -> 'Hill Climb Racing'
         'microsoft.microsoftsolitairecollection.exe' -> 'Microsoft Solitaire Collection'
         'code.exe' -> 'Code'
    """
    import re
    stem = re.sub(r"\.exe$", "", process_name, flags=re.IGNORECASE)
    if "." in stem:
        parts = stem.split(".")
        if len(parts[-1]) >= 3:
            stem = parts[-1]

    # Handle known compound prefixes
    s_lower = stem.lower()
    for prefix, repl in [("hp", "HP "), ("ms", "MS ")]:
        if s_lower.startswith(prefix) and len(s_lower) > len(prefix):
            stem = repl + stem[len(prefix):]
            break

    # Split known compound app words if squished together
    known_words = [
        "microsoft", "support", "assistant", "hill", "climb", "racing", 
        "solitaire", "collection", "desktop", "player", "manager", "studio", 
        "video", "audio", "music", "photo", "games", "game", "center", 
        "settings", "system", "client", "browser", "viewer", "editor", 
        "reader", "connect", "security", "health", "diagnostics",
        "privacy", "control", "presence", "smart", "energy", "star"
    ]
    for kw in sorted(known_words, key=len, reverse=True):
        pattern = re.compile(rf"(?<!\b)({kw})", re.IGNORECASE)
        stem = pattern.sub(r" \1", stem)

    # Insert space before camel/pascal case transitions
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    cleaned = stem.replace("-", " ").replace("_", " ").strip().title()
    # Normalize known abbreviations
    cleaned = re.sub(r"\bHp\b", "HP", cleaned)
    cleaned = re.sub(r"\bVs\b", "VS", cleaned)
    cleaned = re.sub(r"\bUi\b", "UI", cleaned)
    cleaned = re.sub(r"\bMs\b", "MS", cleaned)
    return cleaned


def get_uwp_manifest_display_name(package_dir: Path) -> str:
    """
    Extracts the user-facing DisplayName from an installed UWP/Store AppxManifest.xml.
    """
    manifest = package_dir / "AppxManifest.xml"
    if not manifest.exists():
        return ""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(manifest)
        root = tree.getroot()
        for child in root:
            if child.tag.endswith("Properties"):
                for p in child:
                    if p.tag.endswith("DisplayName") and p.text and not p.text.startswith("ms-resource:") and not p.text.startswith("@{"):
                        return p.text.strip()
            if child.tag.endswith("Applications"):
                for app in child:
                    for app_child in app:
                        if app_child.tag.endswith("VisualElements"):
                            dn = app_child.attrib.get("DisplayName", "")
                            if dn and not dn.startswith("ms-resource:") and not dn.startswith("@{"):
                                return dn.strip()
    except Exception:
        pass
    return ""


_installed_apps_cache: dict[str, tuple[str, str]] = {}
_installed_apps_cache_time: float = 0.0


def get_installed_user_applications(force_refresh: bool = False) -> dict[str, tuple[str, str]]:
    """
    Discovers installed user-facing desktop applications on the system
    (even when they are closed/not running) by querying Start Menu shortcuts,
    Windows App Paths registry keys, user program directories, and Store packages.
    Returns: dict mapping process_name (lowercase) -> (display_name, exe_path)
    """
    global _installed_apps_cache, _installed_apps_cache_time
    import time
    import os
    now = time.time()
    if not force_refresh and _installed_apps_cache and (now - _installed_apps_cache_time < 300.0):
        return dict(_installed_apps_cache)

    apps: dict[str, tuple[str, str]] = {}

    # 1. Start Menu Shortcuts (User & System)
    dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    try:
        import win32com.client
        wscript = win32com.client.Dispatch("WScript.Shell")
        for base in dirs:
            if not base.exists():
                continue
            for lnk in base.rglob("*.lnk"):
                try:
                    target = wscript.CreateShortCut(str(lnk)).Targetpath
                    if target and target.lower().endswith(".exe"):
                        p = Path(target)
                        name = p.name.lower()
                        if name not in apps and is_safe_lock_target(str(p), name):
                            if is_user_facing_application(None, str(p), name):
                                # Prioritize PE product name -> shortcut name -> fallback
                                disp = get_executable_product_name(str(p)) or lnk.stem or clean_fallback_name(name)
                                apps[name] = (disp.strip(), str(p))
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Registry App Paths (HKLM & HKCU, 64-bit and 32-bit)
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
            ):
                try:
                    with winreg.OpenKey(root, subkey) as k:
                        num_keys = winreg.QueryInfoKey(k)[0]
                        for i in range(num_keys):
                            try:
                                app_name = winreg.EnumKey(k, i).lower()
                                if not app_name.endswith(".exe"):
                                    continue
                                with winreg.OpenKey(k, app_name) as ak:
                                    p_str, _ = winreg.QueryValueEx(ak, "")
                                    if p_str and Path(p_str).exists():
                                        p = Path(p_str)
                                        name = p.name.lower()
                                        if name not in apps and is_safe_lock_target(str(p), name):
                                            if is_user_facing_application(None, str(p), name):
                                                disp = get_executable_product_name(str(p)) or clean_fallback_name(name)
                                                apps[name] = (disp.strip(), str(p))
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # 3. LocalAppData Programs directory
    try:
        local_progs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"
        if local_progs.exists():
            for exe in local_progs.glob("*/*.exe"):
                try:
                    name = exe.name.lower()
                    if name not in apps and is_safe_lock_target(str(exe), name):
                        if is_user_facing_application(None, str(exe), name):
                            disp = get_executable_product_name(str(exe)) or clean_fallback_name(name)
                            apps[name] = (disp.strip(), str(exe))
                except Exception:
                    pass
    except Exception:
        pass

    # 4. Microsoft Store / UWP Applications (e.g. Spotify, WhatsApp, HP Support Assistant, Games)
    try:
        import winreg
        uwp_key_path = r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uwp_key_path) as k:
            num_pkgs = winreg.QueryInfoKey(k)[0]
            for idx in range(num_pkgs):
                pkg_name = winreg.EnumKey(k, idx)
                pkg_lower = pkg_name.lower()
                # Skip known internal OS/framework packages
                if any(fw in pkg_lower for fw in ("vclibs", "directx", "ui.xaml", "services.store", "appinstaller", "microsoft.windows.")):
                    continue
                try:
                    with winreg.OpenKey(k, pkg_name) as pk:
                        try:
                            root_folder, _ = winreg.QueryValueEx(pk, "PackageRootFolder")
                        except Exception:
                            continue
                        if not root_folder:
                            continue
                        rf_path = Path(root_folder)
                        if not rf_path.exists():
                            continue

                        # Resolve friendly display name for package
                        pkg_display = ""
                        try:
                            dn, _ = winreg.QueryValueEx(pk, "DisplayName")
                            if dn and not dn.startswith("ms-resource:") and not dn.startswith("@{"):
                                pkg_display = dn.strip()
                        except Exception:
                            pass

                        if not pkg_display:
                            pkg_display = get_uwp_manifest_display_name(rf_path)

                        for exe_file in rf_path.glob("*.exe"):
                            name = exe_file.name.lower()
                            if name in apps:
                                continue
                            disp = pkg_display or get_executable_product_name(str(exe_file)) or clean_fallback_name(name)
                            if is_safe_lock_target(str(exe_file), name) and is_user_facing_application(None, str(exe_file), name, display_name=disp):
                                apps[name] = (disp.strip(), str(exe_file))
                except Exception:
                    pass
    except Exception:
        pass

    # 5. Standard common application locations (Steam, Spotify, Discord, etc.)
    common_targets = [
        Path(r"C:\Program Files (x86)\Steam\steam.exe"),
        Path(r"C:\Program Files\Steam\steam.exe"),
        Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Spotify" / "Spotify.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Discord" / "Update.exe",
    ]
    for target in common_targets:
        try:
            if target.exists():
                name = target.name.lower()
                if name not in apps and is_safe_lock_target(str(target), name) and is_user_facing_application(None, str(target), name):
                    disp = get_executable_product_name(str(target)) or clean_fallback_name(name)
                    apps[name] = (disp.strip(), str(target))
        except Exception:
            pass

    _installed_apps_cache = apps
    _installed_apps_cache_time = now
    return dict(apps)


def get_all_discoverable_applications() -> list[tuple[str, str, str]]:
    """
    Returns a unified list of (process_name, display_name, exe_path) for all
    installed user-facing applications and currently running user-facing processes.
    Sorted alphabetically by display name.
    """
    installed = get_installed_user_applications()
    combined: dict[str, tuple[str, str]] = dict(installed)

    # Supplement with currently running user-facing processes
    try:
        import psutil
        for proc in psutil.process_iter(["name", "exe", "pid"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if not name or not name.endswith(".exe") or name in combined:
                    continue
                exe = proc.info.get("exe") or ""
                pid = proc.info.get("pid")
                if is_safe_lock_target(exe, name):
                    disp = get_executable_product_name(exe) if exe else ""
                    if not disp:
                        disp = clean_fallback_name(name)
                    if is_user_facing_application(pid, exe, name, display_name=disp):
                        combined[name] = (disp.strip(), exe)
            except Exception:
                pass
    except Exception:
        pass

    result = [(name, disp if disp else clean_fallback_name(name), path) for name, (disp, path) in combined.items()]
    result.sort(key=lambda item: item[1].lower())
    return result


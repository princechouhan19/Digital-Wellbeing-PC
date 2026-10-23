from __future__ import annotations

import re
from functools import lru_cache

from core.constants import AppCategory

_GAME_PATH_INDICATORS = (
    "\\steamapps\\common\\",
    "\\epic games\\",
    "\\riot games\\",
    "\\valorant\\",
    "\\league of legends\\",
    "\\xboxgames\\",
    "\\ea games\\",
    "\\origin games\\",
    "\\ubisoft\\ubisoft game launcher\\games\\",
    "\\gog galaxy\\games\\",
    "\\blizzard\\",
    "\\battlenet\\",
    "\\games\\",
)

_EXCLUDED_PATH_EXES = {
    "unins000.exe",
    "uninstall.exe",
    "dxsetup.exe",
    "vcredist_x64.exe",
    "vcredist_x86.exe",
    "ue4prereqsetup_x64.exe",
    "crashreportclient.exe",
    "unitycrashhandler64.exe",
    "unitycrashhandler32.exe",
}

_RULES: list[tuple[re.Pattern, AppCategory]] = [
    (re.compile(r"chrome|firefox|msedge|brave|opera|operagx|vivaldi|iexplore|safari|arc|waterfox|librewolf|tor|atlas|comet|zen|chromium|floorp|sidekick|duckduckgo", re.I), AppCategory.BROWSER),
    (re.compile(r"code|pycharm|idea|devenv|studio|vim|nvim|emacs|sublime|atom|notepad\+\+|rider|clion|webstorm|goland|eclipse|netbeans|cursor", re.I), AppCategory.PROGRAMMING),
    (re.compile(r"steam|epic|gog|itch|valorant|cs2|csgo|minecraft|fortnite|league|riot|battlenet|origin|uplay|xbox|gamebar|overwatch|dota|apex|rocketleague|forza|starfield|haloinfinite|diablo|baldursgate|alanwake|cyberpunk|eldenring|gta|roblox|genshin|honkai|worldofwarcraft|pubg|destiny|rainbowsix|r6s|smite|paladins|tarkov|rust|fallguys|hades|terraria|stardew|civilization|sims|cities|skyrim|witcher|fallout|half-life|portal|left4dead|payday|monsterhunter|tekken|streetfighter|guiltygear|mortal_kombat|farcry|assassinscreed|battlefield|cod|callofduty|modernwarfare|warzone|fifa|fc24|nba2k|madden|f1_|^bg3$|^hl2$|^dota2$", re.I), AppCategory.GAMING),
    (re.compile(r"teams|slack|discord|zoom|skype|telegram|whatsapp|signal|outlook|thunderbird|mattermost|rocketchat", re.I), AppCategory.COMMUNICATION),
    (re.compile(r"excel|word|powerpoint|onenote|notion|obsidian|logseq|evernote|libreoffice|winword|powerpnt|soffice|acroRd|foxit|figma|canva", re.I), AppCategory.PRODUCTIVITY),
    (re.compile(r"vlc|mpc|mpv|wmplayer|spotify|netflix|hulu|youtube|potplayer|kodi|plex|foobar|winamp|itunes|musicbee", re.I), AppCategory.ENTERTAINMENT),
    (re.compile(r"explorer|taskmgr|regedit|mmc|services|devmgmt|compmgmt|control|cmd|powershell|wt|conhost|dwm|csrss|lsass|winlogon|svchost|applicationframehost", re.I), AppCategory.SYSTEM),
    (re.compile(r"7z|winrar|filezilla|putty|winscp|rufus|etcher|veracrypt|cryptomator|keepass|bitwarden|sharex|obs64|obs32", re.I), AppCategory.UTILITIES),
    (re.compile(r"anki|duolingo|kindle|calibre|sumatra|adobe.*reader|evince", re.I), AppCategory.EDUCATION),
    (re.compile(r"twitter|x\.exe|instagram|facebook|tiktok|snapchat|reddit|linkedin", re.I), AppCategory.SOCIAL),
]


_LAUNCHER_KEYWORDS = {
    "steam", "steam.exe", "epicgameslauncher", "epicgameslauncher.exe",
    "riotclient", "riotclientservices", "riotclientservices.exe",
    "battle.net", "battle.net.exe", "battlenet", "eadesktop", "eadesktop.exe",
    "origin", "origin.exe", "upc", "upc.exe", "ubisoftconnect", "ubisoftconnect.exe",
    "xboxpcapp", "xboxpcapp.exe", "xboxapp", "gamebar", "gamebar.exe",
    "goggalaxy", "galaxyclient.exe",
}


@lru_cache(maxsize=1024)
def categorize_with_reason(process_name: str, exe_path: str = "") -> tuple[AppCategory, str, str]:
    name_lower = process_name.lower()
    name = name_lower.removesuffix(".exe")

    # Layer 1: Check Path Heuristics for PC Games
    if exe_path and name_lower not in _EXCLUDED_PATH_EXES:
        path_lower = exe_path.lower().replace("/", "\\")
        for indicator in _GAME_PATH_INDICATORS:
            if indicator in path_lower:
                return AppCategory.GAMING, f"Path match: {indicator.strip('\\')}", ""

    # Layer 2: Check Regex Rules
    for pattern, category in _RULES:
        if pattern.search(name):
            game_reason = ""
            launcher_reason = ""
            if category == AppCategory.GAMING:
                if name_lower in _LAUNCHER_KEYWORDS or "client" in name_lower or "launcher" in name_lower or "service" in name_lower:
                    launcher_reason = f"Launcher regex match ({name})"
                else:
                    game_reason = f"Game regex match ({pattern.pattern})"
            return category, game_reason, launcher_reason

    return AppCategory.OTHER, "", ""


@lru_cache(maxsize=1024)
def categorize(process_name: str, exe_path: str = "") -> AppCategory:
    return categorize_with_reason(process_name, exe_path)[0]



def display_name(process_name: str) -> str:
    name = process_name.lower().removesuffix(".exe")
    overrides = {
        "chrome": "Google Chrome",
        "msedge": "Microsoft Edge",
        "firefox": "Mozilla Firefox",
        "brave": "Brave Browser",
        "opera": "Opera",
        "operagx": "Opera GX",
        "vivaldi": "Vivaldi",
        "arc": "Arc Browser",
        "atlas": "Atlas Browser",
        "comet": "Comet Browser",
        "zen": "Zen Browser",
        "chromium": "Chromium",
        "floorp": "Floorp Browser",
        "waterfox": "Waterfox",
        "librewolf": "LibreWolf",
        "tor": "Tor Browser",
        "duckduckgo": "DuckDuckGo Browser",
        "sidekick": "Sidekick Browser",
        "code": "Visual Studio Code",
        "devenv": "Visual Studio",
        "pycharm64": "PyCharm",
        "pycharm": "PyCharm",
        "idea64": "IntelliJ IDEA",
        "winword": "Microsoft Word",
        "excel": "Microsoft Excel",
        "powerpnt": "Microsoft PowerPoint",
        "outlook": "Microsoft Outlook",
        "teams": "Microsoft Teams",
        "discord": "Discord",
        "slack": "Slack",
        "zoom": "Zoom",
        "spotify": "Spotify",
        "steam": "Steam",
        "epicgameslauncher": "Epic Games Launcher",
        "battle.net": "Battle.net",
        "eadesktop": "EA App",
        "upc": "Ubisoft Connect",
        "xboxpcapp": "Xbox",
        "explorer": "File Explorer",
        "taskmgr": "Task Manager",
        "powershell": "PowerShell",
        "wt": "Windows Terminal",
        "cmd": "Command Prompt",
        "valorant": "Valorant",
        "valorant-win64-shipping": "Valorant",
        "riotclient": "Riot Client",
        "riotclientservices": "Riot Client",
        "leagueoflegends": "League of Legends",
        "leagueclient": "League of Legends",
        "league client": "League of Legends",
        "csgo": "Counter-Strike: Global Offensive",
        "cs2": "Counter-Strike 2",
        "fortniteclient-win64-shipping": "Fortnite",
        "dota2": "Dota 2",
        "rocketleague": "Rocket League",
        "apex": "Apex Legends",
        "r6": "Tom Clancy's Rainbow Six Siege",
    }
    return overrides.get(name, process_name.removesuffix(".exe").replace("_", " ").replace("-", " ").title())

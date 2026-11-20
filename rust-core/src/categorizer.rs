//! Deterministic process-name and executable-path categorization.
//!
//! Keep rule order and substring behavior aligned with `tracker/categorizer.py`.
//! Shared cases under `rust-core/tests/fixtures` are the cross-language contract.

pub const CATEGORY_OTHER: u32 = 0;
pub const CATEGORY_BROWSER: u32 = 1;
pub const CATEGORY_PROGRAMMING: u32 = 2;
pub const CATEGORY_GAMING: u32 = 3;
pub const CATEGORY_COMMUNICATION: u32 = 4;
pub const CATEGORY_PRODUCTIVITY: u32 = 5;
pub const CATEGORY_ENTERTAINMENT: u32 = 6;
pub const CATEGORY_SYSTEM: u32 = 7;
pub const CATEGORY_UTILITIES: u32 = 8;
pub const CATEGORY_EDUCATION: u32 = 9;
pub const CATEGORY_SOCIAL: u32 = 10;

pub const REASON_NONE: u32 = 0;
pub const REASON_PATH: u32 = 1;
pub const REASON_LAUNCHER: u32 = 2;
pub const REASON_GAME: u32 = 3;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Categorization {
    pub category: u32,
    pub reason_kind: u32,
    pub reason_value: String,
}

const GAME_PATH_INDICATORS: &[(&str, &str)] = &[
    ("\\steamapps\\common\\", "steamapps\\common"),
    ("\\epic games\\", "epic games"),
    ("\\riot games\\", "riot games"),
    ("\\valorant\\", "valorant"),
    ("\\league of legends\\", "league of legends"),
    ("\\xboxgames\\", "xboxgames"),
    ("\\ea games\\", "ea games"),
    ("\\origin games\\", "origin games"),
    (
        "\\ubisoft\\ubisoft game launcher\\games\\",
        "ubisoft\\ubisoft game launcher\\games",
    ),
    ("\\gog galaxy\\games\\", "gog galaxy\\games"),
    ("\\blizzard\\", "blizzard"),
    ("\\battlenet\\", "battlenet"),
    ("\\games\\", "games"),
];

const EXCLUDED_PATH_EXES: &[&str] = &[
    "unins000.exe",
    "uninstall.exe",
    "dxsetup.exe",
    "vcredist_x64.exe",
    "vcredist_x86.exe",
    "ue4prereqsetup_x64.exe",
    "crashreportclient.exe",
    "unitycrashhandler64.exe",
    "unitycrashhandler32.exe",
];

const BROWSER_TOKENS: &[&str] = &[
    "chrome", "firefox", "msedge", "brave", "opera", "operagx", "vivaldi", "iexplore",
    "safari", "arc", "waterfox", "librewolf", "tor", "atlas", "comet", "zen", "chromium",
    "floorp", "sidekick", "duckduckgo",
];
const PROGRAMMING_TOKENS: &[&str] = &[
    "code", "pycharm", "idea", "devenv", "studio", "vim", "nvim", "emacs", "sublime",
    "atom", "notepad++", "rider", "clion", "webstorm", "goland", "eclipse", "netbeans",
    "cursor",
];
const GAMING_TOKENS: &[&str] = &[
    "steam", "epic", "gog", "itch", "valorant", "cs2", "csgo", "minecraft", "fortnite",
    "league", "riot", "battlenet", "origin", "uplay", "xbox", "gamebar", "overwatch", "dota",
    "apex", "rocketleague", "forza", "starfield", "haloinfinite", "diablo", "baldursgate",
    "alanwake", "cyberpunk", "eldenring", "gta", "roblox", "genshin", "honkai",
    "worldofwarcraft", "pubg", "destiny", "rainbowsix", "r6s", "smite", "paladins", "tarkov",
    "rust", "fallguys", "hades", "terraria", "stardew", "civilization", "sims", "cities",
    "skyrim", "witcher", "fallout", "half-life", "portal", "left4dead", "payday", "monsterhunter",
    "tekken", "streetfighter", "guiltygear", "mortal_kombat", "farcry", "assassinscreed",
    "battlefield", "cod", "callofduty", "modernwarfare", "warzone", "fifa", "fc24", "nba2k",
    "madden", "f1_",
];
const COMMUNICATION_TOKENS: &[&str] = &[
    "teams", "slack", "discord", "zoom", "skype", "telegram", "whatsapp", "signal", "outlook",
    "thunderbird", "mattermost", "rocketchat",
];
const PRODUCTIVITY_TOKENS: &[&str] = &[
    "excel", "word", "powerpoint", "onenote", "notion", "obsidian", "logseq", "evernote",
    "libreoffice", "winword", "powerpnt", "soffice", "acrord", "foxit", "figma", "canva",
];
const ENTERTAINMENT_TOKENS: &[&str] = &[
    "vlc", "mpc", "mpv", "wmplayer", "spotify", "netflix", "hulu", "youtube", "potplayer",
    "kodi", "plex", "foobar", "winamp", "itunes", "musicbee",
];
const SYSTEM_TOKENS: &[&str] = &[
    "explorer", "taskmgr", "regedit", "mmc", "services", "devmgmt", "compmgmt", "control", "cmd",
    "powershell", "wt", "conhost", "dwm", "csrss", "lsass", "winlogon", "svchost",
    "applicationframehost",
];
const UTILITIES_TOKENS: &[&str] = &[
    "7z", "winrar", "filezilla", "putty", "winscp", "rufus", "etcher", "veracrypt",
    "cryptomator", "keepass", "bitwarden", "sharex", "obs64", "obs32",
];
const EDUCATION_TOKENS: &[&str] = &["anki", "duolingo", "kindle", "calibre", "sumatra", "evince"];
const SOCIAL_TOKENS: &[&str] = &[
    "twitter", "x.exe", "instagram", "facebook", "tiktok", "snapchat", "reddit", "linkedin",
];

const LAUNCHER_KEYWORDS: &[&str] = &[
    "steam", "steam.exe", "epicgameslauncher", "epicgameslauncher.exe", "riotclient",
    "riotclientservices", "riotclientservices.exe", "battle.net", "battle.net.exe", "battlenet",
    "eadesktop", "eadesktop.exe", "origin", "origin.exe", "upc", "upc.exe", "ubisoftconnect",
    "ubisoftconnect.exe", "xboxpcapp", "xboxpcapp.exe", "xboxapp", "gamebar", "gamebar.exe",
    "goggalaxy", "galaxyclient.exe",
];

fn contains_any(value: &str, tokens: &[&str]) -> bool {
    tokens.iter().any(|token| value.contains(*token))
}

fn contains_after(value: &str, first: &str, second: &str) -> bool {
    value
        .find(first)
        .map(|index| value[index + first.len()..].contains(second))
        .unwrap_or(false)
}

/// Return a category code and a compact reason descriptor.
///
/// Reason kinds: none (0), path match (1), launcher match (2), game regex (3).
pub fn categorize_process(process_name: &str, exe_path: &str) -> Categorization {
    let name_lower = process_name.to_lowercase();
    let name = name_lower.strip_suffix(".exe").unwrap_or(&name_lower);

    let excluded_from_path = EXCLUDED_PATH_EXES
        .iter()
        .any(|&excluded| excluded == name_lower.as_str());
    if !exe_path.is_empty() && !excluded_from_path {
        let path_lower = exe_path.to_lowercase().replace('/', "\\");
        for (indicator, reason) in GAME_PATH_INDICATORS {
            if path_lower.contains(*indicator) {
                return Categorization {
                    category: CATEGORY_GAMING,
                    reason_kind: REASON_PATH,
                    reason_value: (*reason).to_owned(),
                };
            }
        }
    }

    let category = if contains_any(name, BROWSER_TOKENS) {
        CATEGORY_BROWSER
    } else if contains_any(name, PROGRAMMING_TOKENS) {
        CATEGORY_PROGRAMMING
    } else if contains_any(name, GAMING_TOKENS) || name == "bg3" || name == "hl2" {
        let is_launcher = LAUNCHER_KEYWORDS
            .iter()
            .any(|&keyword| keyword == name_lower.as_str())
            || name_lower.contains("client")
            || name_lower.contains("launcher")
            || name_lower.contains("service");
        return Categorization {
            category: CATEGORY_GAMING,
            reason_kind: if is_launcher { REASON_LAUNCHER } else { REASON_GAME },
            reason_value: if is_launcher { name.to_owned() } else { String::new() },
        };
    } else if contains_any(name, COMMUNICATION_TOKENS) {
        CATEGORY_COMMUNICATION
    } else if contains_any(name, PRODUCTIVITY_TOKENS) {
        CATEGORY_PRODUCTIVITY
    } else if contains_any(name, ENTERTAINMENT_TOKENS) {
        CATEGORY_ENTERTAINMENT
    } else if contains_any(name, SYSTEM_TOKENS) {
        CATEGORY_SYSTEM
    } else if contains_any(name, UTILITIES_TOKENS) {
        CATEGORY_UTILITIES
    } else if contains_any(name, EDUCATION_TOKENS) || contains_after(name, "adobe", "reader")
    {
        CATEGORY_EDUCATION
    } else if contains_any(name, SOCIAL_TOKENS) {
        CATEGORY_SOCIAL
    } else {
        CATEGORY_OTHER
    };

    Categorization {
        category,
        reason_kind: REASON_NONE,
        reason_value: String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::{categorize_process, CATEGORY_GAMING, CATEGORY_OTHER, REASON_LAUNCHER, REASON_PATH};

    #[test]
    fn game_paths_and_launchers_keep_distinct_reason_kinds() {
        let path = categorize_process("unknown.exe", r"C:\Games\Indie\unknown.exe");
        assert_eq!(path.category, CATEGORY_GAMING);
        assert_eq!(path.reason_kind, REASON_PATH);
        assert_eq!(path.reason_value, "games");

        let launcher = categorize_process("Steam.exe", "");
        assert_eq!(launcher.category, CATEGORY_GAMING);
        assert_eq!(launcher.reason_kind, REASON_LAUNCHER);
        assert_eq!(launcher.reason_value, "steam");
    }

    #[test]
    fn excluded_installers_are_not_classified_by_game_path() {
        let result = categorize_process("unins000.exe", r"C:\Games\A\unins000.exe");
        assert_eq!(result.category, CATEGORY_OTHER);
        assert_eq!(result.reason_kind, 0);
    }
}

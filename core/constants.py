from __future__ import annotations

from enum import Enum, auto


class AppCategory(str, Enum):
    BROWSER = "Browser"
    PROGRAMMING = "Programming"
    GAMING = "Gaming"
    COMMUNICATION = "Communication"
    PRODUCTIVITY = "Productivity"
    ENTERTAINMENT = "Entertainment"
    SYSTEM = "System"
    UTILITIES = "Utilities"
    EDUCATION = "Education"
    SOCIAL = "Social"
    FINANCE = "Finance"
    OTHER = "Other"


class TimePeriod(str, Enum):
    TODAY = "Today"
    WEEK = "This Week"
    MONTH = "This Month"


class EventType(str, Enum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    IDLE_START = "idle_start"
    IDLE_END = "idle_end"
    LOCK = "lock"
    UNLOCK = "unlock"
    SLEEP = "sleep"
    RESUME = "resume"


APP_NAME = "Digital Wellbeing"
from core.version import get_version
APP_VERSION = get_version()
APP_AUMID = "PrinceChouhan.DigitalWellbeing.App"
DB_FILENAME = "digital_wellbeing.db"
LOG_FILENAME = "digital_wellbeing.log"

POLL_INTERVAL_MS = 500
DEFAULT_IDLE_THRESHOLD_S = 300
MAX_SESSION_GAP_S = 30

# Apple system palette — category color mapping (Aurora design system)
# Dark-mode variants (canonical); light variants in CATEGORY_COLORS_LIGHT.
CATEGORY_COLORS: dict[AppCategory, str] = {
    AppCategory.BROWSER: "#0A84FF",        # systemBlue
    AppCategory.OTHER: "#63E6E2",          # systemMint
    AppCategory.PRODUCTIVITY: "#30D158",   # systemGreen
    AppCategory.SYSTEM: "#8E8E93",         # systemGray

    AppCategory.COMMUNICATION: "#64D2FF",  # systemCyan
    AppCategory.ENTERTAINMENT: "#FF9F0A",  # systemOrange
    AppCategory.GAMING: "#BF5AF2",         # systemPurple
    AppCategory.FINANCE: "#FFD60A",        # systemYellow
    AppCategory.EDUCATION: "#40C8E0",      # systemTeal
    AppCategory.PROGRAMMING: "#5E5CE6",    # systemIndigo
    AppCategory.UTILITIES: "#AC8E68",      # systemBrown
    AppCategory.SOCIAL: "#FF375F",         # systemPink
}

CATEGORY_COLORS_LIGHT: dict[AppCategory, str] = {
    AppCategory.BROWSER: "#007AFF",
    AppCategory.OTHER: "#00C7BE",
    AppCategory.PRODUCTIVITY: "#34C759",
    AppCategory.SYSTEM: "#8E8E93",

    AppCategory.COMMUNICATION: "#32ADE6",
    AppCategory.ENTERTAINMENT: "#FF9500",
    AppCategory.GAMING: "#AF52DE",
    AppCategory.FINANCE: "#E6A800",
    AppCategory.EDUCATION: "#30B0C7",
    AppCategory.PROGRAMMING: "#5856D6",
    AppCategory.UTILITIES: "#A2845E",
    AppCategory.SOCIAL: "#FF2D55",
}


def get_category_colors(dark: bool = True) -> dict:
    """Theme-aware category color map."""
    return CATEGORY_COLORS if dark else CATEGORY_COLORS_LIGHT

CATEGORY_ICONS: dict[AppCategory, str] = {
    AppCategory.BROWSER: "globe",
    AppCategory.PROGRAMMING: "code",
    AppCategory.GAMING: "gamepad",
    AppCategory.COMMUNICATION: "message",
    AppCategory.PRODUCTIVITY: "target",
    AppCategory.ENTERTAINMENT: "play",
    AppCategory.SYSTEM: "system",
    AppCategory.UTILITIES: "system",
    AppCategory.EDUCATION: "info",
    AppCategory.SOCIAL: "user",
    AppCategory.FINANCE: "bar_chart",
    AppCategory.OTHER: "apps",
}

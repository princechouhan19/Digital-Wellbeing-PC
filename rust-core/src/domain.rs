//! Deterministic, platform-independent domain helpers shared with the Python app.
//!
//! Keep the title rules in sync with `tracker/browser_domain.py`. The shared
//! TSV corpus under `rust-core/tests/fixtures` is exercised by both languages.

const DOMAIN_TLDS: &[&str] = &[
    "com", "org", "net", "io", "co", "ai", "tv", "app", "dev", "edu", "gov", "in",
    "uk", "de", "jp", "ca", "me", "xyz", "so", "gg", "to", "cc", "tech", "info", "biz",
    "site", "cloud", "us",
];

/// Normalize a domain-like value in the same way as the app's website-limit
/// helper: remove a scheme, path/query/fragment, port, optional `www.`, and
/// surrounding dots/spaces. This intentionally does not validate public suffixes.
pub fn normalize_domain(raw: &str) -> String {
    let mut value = raw.trim().to_lowercase();
    if let Some(rest) = value.strip_prefix("https://") {
        value = rest.to_owned();
    } else if let Some(rest) = value.strip_prefix("http://") {
        value = rest.to_owned();
    }

    let end = value
        .find(|character: char| matches!(character, '/' | '?' | '#' | ':'))
        .unwrap_or(value.len());
    value.truncate(end);
    let value = value.trim_matches(|character| character == '.' || character == ' ');
    let value = value.strip_prefix("www.").unwrap_or(value);
    value.trim_matches(|character| character == '.' || character == ' ').to_owned()
}

/// Return whether a normalized host is the rule host or one of its subdomains.
/// Path matching belongs to the URL-rule layer and is deliberately not done here.
pub fn host_matches(host: &str, rule_host: &str) -> bool {
    let host = normalize_domain(host);
    let rule = normalize_domain(rule_host);
    if host.is_empty() || rule.is_empty() {
        return false;
    }
    host == rule || host.ends_with(&format!(".{rule}"))
}

/// Strip a known browser suffix and optional Edge profile / multi-page suffix.
pub fn clean_browser_title(title: &str) -> String {
    let mut cleaned = title.trim();

    if let Some(without_edge) = strip_edge_suffix(cleaned) {
        cleaned = without_edge;
    } else {
        // Longer suffixes precede shorter ones (Opera GX before Opera, etc.).
        const DASH_SUFFIXES: &[&str] = &[
            "Google Chrome",
            "Opera GX",
            "Tor Browser",
            "Zen Browser",
            "DuckDuckGo",
            "Waterfox",
            "LibreWolf",
            "Chromium",
            "Vivaldi",
            "Brave",
            "Opera",
            "Atlas",
            "Comet",
            "Firefox",
            "Mozilla Firefox",
            "Arc",
            "Zen",
        ];
        for suffix in DASH_SUFFIXES {
            let separators: &[char] = if *suffix == "Firefox" || *suffix == "Mozilla Firefox" {
                &['-', '–', '—']
            } else {
                &['-']
            };
            if let Some(prefix) = strip_dash_suffix(cleaned, suffix, separators) {
                cleaned = prefix;
                break;
            }
        }
    }

    cleaned.trim().to_owned()
}

/// Extract a site domain from a browser title, following the Python tracker’s
/// known-service-first, then explicit-domain behavior. Empty means no match.
pub fn extract_domain_from_title(title: &str) -> String {
    let cleaned = clean_browser_title(title);
    if cleaned.is_empty()
        || ["new tab", "settings", "downloads", "history", "extensions", "untitled"]
            .iter()
            .any(|reserved| cleaned.eq_ignore_ascii_case(reserved))
    {
        return String::new();
    }

    let lower = cleaned.to_ascii_lowercase();
    if let Some(domain) = known_service_domain(&lower) {
        return domain.to_owned();
    }
    generic_domain(&cleaned).unwrap_or_default()
}

fn strip_dash_suffix<'a>(value: &'a str, suffix: &str, separators: &[char]) -> Option<&'a str> {
    let value = value.trim_end();
    if value.len() < suffix.len() {
        return None;
    }
    let split = value.len() - suffix.len();
    let (prefix, tail) = value.split_at(split);
    if !tail.eq_ignore_ascii_case(suffix) {
        return None;
    }

    let prefix = prefix.trim_end();
    let (separator_index, separator) = prefix.char_indices().next_back()?;
    if separators.contains(&separator) {
        Some(prefix[..separator_index].trim_end())
    } else {
        None
    }
}

fn strip_edge_suffix(value: &str) -> Option<&str> {
    let mut prefix = strip_dash_suffix(value, "Microsoft Edge", &['-'])?;

    if let Some(without_profile) = strip_dash_suffix(prefix, "Personal", &['-']) {
        prefix = without_profile;
    } else if let Some(without_profile) = strip_dash_suffix(prefix, "Work", &['-']) {
        prefix = without_profile;
    } else if let Some(without_profile) = strip_numbered_edge_profile(prefix) {
        prefix = without_profile;
    }

    strip_edge_multi_page_suffix(prefix).or(Some(prefix.trim()))
}

fn strip_numbered_edge_profile(value: &str) -> Option<&str> {
    let lower = value.to_ascii_lowercase();
    let marker = " - profile ";
    let marker_index = lower.rfind(marker)?;
    let digits = &lower[marker_index + marker.len()..];
    if !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit()) {
        Some(value[..marker_index].trim_end())
    } else {
        None
    }
}

fn strip_edge_multi_page_suffix(value: &str) -> Option<&str> {
    let lower = value.to_ascii_lowercase();
    let marker = " and ";
    let marker_index = lower.rfind(marker)?;
    let words: Vec<&str> = lower[marker_index + marker.len()..]
        .split_ascii_whitespace()
        .collect();
    if words.len() == 3
        && !words[0].is_empty()
        && words[0].bytes().all(|byte| byte.is_ascii_digit())
        && words[1] == "more"
        && (words[2] == "page" || words[2] == "pages")
    {
        Some(value[..marker_index].trim_end())
    } else {
        None
    }
}

fn is_word_character(character: char) -> bool {
    character.is_alphanumeric() || character == '_'
}

fn has_word(text: &str, word: &str) -> bool {
    text.match_indices(word).any(|(start, matched)| {
        let end = start + matched.len();
        let before_is_word = text[..start]
            .chars()
            .next_back()
            .map_or(false, is_word_character);
        let after_is_word = text[end..]
            .chars()
            .next()
            .map_or(false, is_word_character);
        !before_is_word && !after_is_word
    })
}

fn has_adjacent_words(text: &str, first: &str, second: &str) -> bool {
    text.match_indices(first).any(|(start, matched)| {
        let before_is_word = text[..start]
            .chars()
            .next_back()
            .map_or(false, is_word_character);
        if before_is_word {
            return false;
        }
        let end = start + matched.len();
        let rest = text[end..].trim_start_matches(char::is_whitespace);
        if let Some(after_second) = rest.strip_prefix(second) {
            !after_second
                .chars()
                .next()
                .map_or(false, is_word_character)
        } else {
            false
        }
    })
}

fn has_slash_x(text: &str) -> bool {
    text.match_indices('/').any(|(start, _)| {
        let before_is_word = text[..start]
            .chars()
            .next_back()
            .map_or(false, is_word_character);
        if !before_is_word {
            return false;
        }
        let rest = text[start + 1..].trim_start_matches(char::is_whitespace);
        rest.strip_prefix('x')
            .map(|tail| !tail.chars().next().map_or(false, is_word_character))
            .unwrap_or(false)
    })
}

fn has_x_title_prefix(text: &str) -> bool {
    let text = text.trim_start();
    if !text.starts_with('x') {
        return false;
    }
    matches!(
        text[1..].trim_start().chars().next(),
        Some('-' | '–' | '—')
    )
}

fn known_service_domain(lower: &str) -> Option<&'static str> {
    if has_word(lower, "youtube") || lower.contains("youtu.be") {
        Some("youtube.com")
    } else if has_word(lower, "google") {
        Some("google.com")
    } else if has_word(lower, "github") {
        Some("github.com")
    } else if has_word(lower, "reddit") {
        Some("reddit.com")
    } else if has_word(lower, "twitter")
        || has_slash_x(lower)
        || has_x_title_prefix(lower)
        || has_word(lower, "x.com")
    {
        Some("twitter.com")
    } else if has_word(lower, "instagram") {
        Some("instagram.com")
    } else if has_word(lower, "facebook") {
        Some("facebook.com")
    } else if has_word(lower, "netflix") {
        Some("netflix.com")
    } else if has_word(lower, "twitch") {
        Some("twitch.tv")
    } else if has_word(lower, "discord") {
        Some("discord.com")
    } else if has_word(lower, "amazon") {
        Some("amazon.com")
    } else if has_word(lower, "wikipedia") {
        Some("wikipedia.org")
    } else if has_word(lower, "linkedin") {
        Some("linkedin.com")
    } else if has_word(lower, "stackoverflow") {
        Some("stackoverflow.com")
    } else if has_word(lower, "chatgpt") || has_word(lower, "openai") {
        Some("chatgpt.com")
    } else if has_word(lower, "claude") || has_word(lower, "anthropic") {
        Some("claude.ai")
    } else if has_word(lower, "notion") {
        Some("notion.so")
    } else if has_word(lower, "figma") {
        Some("figma.com")
    } else if has_word(lower, "whatsapp") {
        Some("whatsapp.com")
    } else if has_word(lower, "telegram") {
        Some("telegram.org")
    } else if has_word(lower, "slack") {
        Some("slack.com")
    } else if has_word(lower, "spotify") {
        Some("spotify.com")
    } else if has_word(lower, "tiktok") {
        Some("tiktok.com")
    } else if has_word(lower, "pinterest") {
        Some("pinterest.com")
    } else if has_word(lower, "quora") {
        Some("quora.com")
    } else if has_word(lower, "zoom") {
        Some("zoom.us")
    } else if has_adjacent_words(lower, "prime", "video") || has_word(lower, "primevideo") {
        Some("primevideo.com")
    } else if has_word(lower, "disney")
        || has_word(lower, "disneyplus")
        || has_word(lower, "hotstar")
    {
        Some("disneyplus.com")
    } else if has_word(lower, "coursera") {
        Some("coursera.org")
    } else if has_word(lower, "udemy") {
        Some("udemy.com")
    } else if has_word(lower, "leetcode") {
        Some("leetcode.com")
    } else if has_word(lower, "medium") {
        Some("medium.com")
    } else if has_word(lower, "substack") {
        Some("substack.com")
    } else if has_word(lower, "duckduckgo") {
        Some("duckduckgo.com")
    } else if has_word(lower, "bing") {
        Some("bing.com")
    } else if has_word(lower, "canva") {
        Some("canva.com")
    } else {
        None
    }
}

fn generic_domain(text: &str) -> Option<String> {
    let bytes = text.as_bytes();
    for (dot_index, byte) in bytes.iter().enumerate() {
        if *byte != b'.' {
            continue;
        }

        for tld in DOMAIN_TLDS {
            let tld_end = dot_index + 1 + tld.len();
            if tld_end > bytes.len()
                || !text[dot_index + 1..tld_end].eq_ignore_ascii_case(tld)
            {
                continue;
            }
            let after_is_word = text[tld_end..]
                .chars()
                .next()
                .map_or(false, is_word_character);
            if after_is_word {
                continue;
            }

            let mut label_start = dot_index;
            while label_start > 0
                && (bytes[label_start - 1].is_ascii_alphanumeric() || bytes[label_start - 1] == b'-')
            {
                label_start -= 1;
            }
            let label = &bytes[label_start..dot_index];
            if label.is_empty()
                || label.len() > 63
                || !label[0].is_ascii_alphanumeric()
                || !label[label.len() - 1].is_ascii_alphanumeric()
            {
                continue;
            }

            let before_is_word = text[..label_start]
                .chars()
                .next_back()
                .map_or(false, is_word_character);
            if before_is_word {
                continue;
            }

            let mut domain = String::with_capacity(label.len() + 1 + tld.len());
            // `label` is restricted to ASCII letters, digits and hyphens.
            domain.push_str(std::str::from_utf8(label).ok()?);
            domain.push('.');
            domain.push_str(tld);
            return Some(domain.to_ascii_lowercase());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::{clean_browser_title, host_matches, normalize_domain};

    #[test]
    fn removes_edge_profile_and_multi_page_suffixes() {
        assert_eq!(
            clean_browser_title("Title and 3 more pages - Work - Microsoft Edge"),
            "Title"
        );
        assert_eq!(
            clean_browser_title("Title - Profile 2 - Microsoft Edge"),
            "Title"
        );
    }

    #[test]
    fn normalizes_domain_inputs() {
        assert_eq!(
            normalize_domain("HTTPS://WWW.YouTube.com/watch?v=1"),
            "youtube.com"
        );
        assert_eq!(normalize_domain("reddit.com:443"), "reddit.com");
        assert_eq!(normalize_domain("m.youtube.com"), "m.youtube.com");
    }

    #[test]
    fn host_matching_is_label_bounded() {
        assert!(host_matches("www.reddit.com", "reddit.com"));
        assert!(host_matches("old.reddit.com", "reddit.com"));
        assert!(!host_matches("myreddit.com", "reddit.com"));
        assert!(!host_matches("reddit.com.org", "reddit.com"));
    }
}

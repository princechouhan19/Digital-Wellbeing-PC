//! Deterministic host/path-prefix rule selection for website protection.
//!
//! URL parsing, percent-decoding and persistence remain in Python. The caller
//! supplies normalized host/path pairs; this module applies the security rule
//! precedence: longest path, then longest host, then block on an exact tie.

use std::ffi::c_char;

pub const ACTION_ALLOW: u8 = 0;
pub const ACTION_BLOCK: u8 = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RuleRef<'a> {
    pub host: &'a str,
    pub path: &'a str,
    pub action: u8,
    pub enabled: bool,
}

/// C-compatible view used by the optional ctypes bridge.
#[repr(C)]
pub struct UrlRuleView {
    pub host: *const c_char,
    pub path: *const c_char,
    pub action: u8,
    pub enabled: u8,
}

pub fn host_matches(url_host: &str, rule_host: &str) -> bool {
    !rule_host.is_empty()
        && (url_host == rule_host
            || url_host
                .strip_suffix(rule_host)
                .map(|prefix| prefix.ends_with('.'))
                .unwrap_or(false))
}

pub fn path_matches(url_path: &str, rule_path: &str) -> bool {
    rule_path.is_empty()
        || url_path == rule_path
        || url_path
            .strip_prefix(rule_path)
            .map(|suffix| suffix.starts_with('/'))
            .unwrap_or(false)
}

/// Return `(action, matching rule index)`, or the supplied default when no rule
/// matches. A lower index wins when every specificity component ties.
pub fn select_rule(
    url_host: &str,
    url_path: &str,
    default_action: u8,
    rules: &[RuleRef<'_>],
) -> (u8, Option<usize>) {
    let mut best_key: Option<(usize, usize, u8)> = None;
    let mut best_action = default_action;
    let mut best_index = None;

    for (index, rule) in rules.iter().enumerate() {
        if !rule.enabled
            || !matches!(rule.action, ACTION_ALLOW | ACTION_BLOCK)
            || !host_matches(url_host, rule.host)
            || !path_matches(url_path, rule.path)
        {
            continue;
        }

        // Python's len(str) counts Unicode code points; use chars().count()
        // rather than Rust's UTF-8 byte length to preserve tie-breaking.
        let key = (
            rule.path.chars().count(),
            rule.host.chars().count(),
            u8::from(rule.action == ACTION_BLOCK),
        );
        if best_key.map(|current| key > current).unwrap_or(true) {
            best_key = Some(key);
            best_action = rule.action;
            best_index = Some(index);
        }
    }

    (best_action, best_index)
}

#[cfg(test)]
mod tests {
    use super::{host_matches, path_matches, select_rule, RuleRef, ACTION_ALLOW, ACTION_BLOCK};

    #[test]
    fn host_and_path_matching_are_label_and_segment_bounded() {
        assert!(host_matches("old.reddit.com", "reddit.com"));
        assert!(!host_matches("notreddit.com", "reddit.com"));
        assert!(path_matches("/r/programming", "/r"));
        assert!(!path_matches("/shorts2", "/shorts"));
    }

    #[test]
    fn selects_most_specific_rule_then_block_on_ties() {
        let rules = [
            RuleRef { host: "reddit.com", path: "/r", action: ACTION_BLOCK, enabled: true },
            RuleRef { host: "reddit.com", path: "/r/programming", action: ACTION_ALLOW, enabled: true },
            RuleRef { host: "reddit.com", path: "/r/programming", action: ACTION_BLOCK, enabled: true },
        ];
        assert_eq!(
            select_rule("reddit.com", "/r/programming", ACTION_ALLOW, &rules),
            (ACTION_BLOCK, Some(2))
        );
    }
}

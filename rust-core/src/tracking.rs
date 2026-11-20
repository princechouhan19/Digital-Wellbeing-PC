//! Pure tracking-session transition policy.
//!
//! The Python tracker remains responsible for Win32 event collection, SQLite,
//! timestamps and side effects. This module selects the action for one fresh
//! foreground sample so the policy can be parity-tested independently.

/// Stable transition codes shared with `core/rust_bridge.py`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum TransitionAction {
    Keep = 0,
    Start = 1,
    AppSwitch = 2,
    IdleSwitch = 3,
    FullscreenTitleUpdate = 4,
    TitleSplit = 5,
    TitleUpdate = 6,
}

/// Select the session action for the current foreground sample.
///
/// The precedence mirrors `TrackingManager._tick`: a missing current app starts
/// a session; process and idle changes take precedence over title changes; a
/// fullscreen game updates its title in place; other titles split only after
/// the existing two-second minimum.
pub fn select_transition(
    has_current_app: bool,
    same_process: bool,
    idle_changed: bool,
    title_changed: bool,
    fullscreen_game: bool,
    session_duration_ms: u64,
) -> TransitionAction {
    if !has_current_app {
        TransitionAction::Start
    } else if !same_process {
        TransitionAction::AppSwitch
    } else if idle_changed {
        TransitionAction::IdleSwitch
    } else if title_changed && fullscreen_game {
        TransitionAction::FullscreenTitleUpdate
    } else if title_changed && session_duration_ms >= 2_000 {
        TransitionAction::TitleSplit
    } else if title_changed {
        TransitionAction::TitleUpdate
    } else {
        TransitionAction::Keep
    }
}

#[cfg(test)]
mod tests {
    use super::{select_transition, TransitionAction};

    #[test]
    fn process_and_idle_changes_precede_title_changes() {
        assert_eq!(
            select_transition(true, false, true, true, false, 5_000),
            TransitionAction::AppSwitch
        );
        assert_eq!(
            select_transition(true, true, true, true, false, 5_000),
            TransitionAction::IdleSwitch
        );
    }

    #[test]
    fn title_policy_keeps_fullscreen_games_and_splits_long_sessions() {
        assert_eq!(
            select_transition(true, true, false, true, true, 5_000),
            TransitionAction::FullscreenTitleUpdate
        );
        assert_eq!(
            select_transition(true, true, false, true, false, 1_999),
            TransitionAction::TitleUpdate
        );
        assert_eq!(
            select_transition(true, true, false, true, false, 2_000),
            TransitionAction::TitleSplit
        );
    }
}

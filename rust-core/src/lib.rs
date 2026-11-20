//! Portable, dependency-free core for the gradual Digital Wellbeing migration.
//!
//! The C ABI is intentionally small and versioned. Python remains the default
//! implementation until Windows parity tests and end-to-end benchmarks justify
//! enabling the native library.

#![deny(unsafe_op_in_unsafe_fn)]

pub mod categorizer;
pub mod domain;
pub mod tracking;
pub mod url_rules;

use std::ffi::{CStr, c_char};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr;

const ABI_VERSION: u32 = 4;
const ERR_NULL_POINTER: isize = -1;
const ERR_INVALID_UTF8: isize = -2;
const ERR_OUTPUT_TOO_SMALL: isize = -3;
const ERR_PANIC: isize = -4;
const ERR_INVALID_ARGUMENT: i32 = -5;

/// ABI version checked by the Python loader before calling into the library.
#[no_mangle]
pub extern "C" fn dw_core_abi_version() -> u32 {
    ABI_VERSION
}

/// Extract a normalized site domain from a NUL-terminated UTF-8 browser title.
///
/// Returns the number of output bytes (excluding NUL), `0` when there is no
/// match, or a negative error code. The caller must provide valid, readable
/// input memory and a writable output buffer of `output_capacity` bytes.
///
/// # Safety
/// `input` must point to a readable NUL-terminated C string. If non-null,
/// `output` must point to a writable buffer of at least `output_capacity` bytes.
#[no_mangle]
pub unsafe extern "C" fn dw_extract_domain_from_title(
    input: *const c_char,
    output: *mut c_char,
    output_capacity: usize,
) -> isize {
    catch_unwind(AssertUnwindSafe(|| {
        if input.is_null() || output.is_null() {
            return ERR_NULL_POINTER;
        }
        // SAFETY: pointer validity and NUL termination are part of this function's contract.
        let title = match unsafe { CStr::from_ptr(input) }.to_str() {
            Ok(title) => title,
            Err(_) => return ERR_INVALID_UTF8,
        };
        let domain = domain::extract_domain_from_title(title);
        // SAFETY: output validity/capacity are part of this function's contract.
        unsafe { write_c_string(output, output_capacity, &domain) }
    }))
    .unwrap_or(ERR_PANIC)
}

/// Normalize a NUL-terminated UTF-8 domain/URL into the app's domain format.
///
/// # Safety
/// `input` must point to a readable NUL-terminated C string. If non-null,
/// `output` must point to a writable buffer of at least `output_capacity` bytes.
#[no_mangle]
pub unsafe extern "C" fn dw_normalize_domain(
    input: *const c_char,
    output: *mut c_char,
    output_capacity: usize,
) -> isize {
    catch_unwind(AssertUnwindSafe(|| {
        if input.is_null() || output.is_null() {
            return ERR_NULL_POINTER;
        }
        // SAFETY: pointer validity and NUL termination are part of this function's contract.
        let raw = match unsafe { CStr::from_ptr(input) }.to_str() {
            Ok(raw) => raw,
            Err(_) => return ERR_INVALID_UTF8,
        };
        let domain = domain::normalize_domain(raw);
        // SAFETY: output validity/capacity are part of this function's contract.
        unsafe { write_c_string(output, output_capacity, &domain) }
    }))
    .unwrap_or(ERR_PANIC)
}

/// Compare a host and a domain rule using exact-or-subdomain matching.
///
/// Returns 1 for a match, 0 for no match, or a negative error code. This is a
/// host-only function; path-prefix rules are handled separately by the app.
///
/// # Safety
/// Both pointers must point to readable NUL-terminated UTF-8 C strings.
#[no_mangle]
pub unsafe extern "C" fn dw_domain_matches(
    host: *const c_char,
    rule_host: *const c_char,
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if host.is_null() || rule_host.is_null() {
            return ERR_NULL_POINTER as i32;
        }
        // SAFETY: pointer validity and NUL termination are part of this function's contract.
        let host = match unsafe { CStr::from_ptr(host) }.to_str() {
            Ok(host) => host,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };
        // SAFETY: pointer validity and NUL termination are part of this function's contract.
        let rule = match unsafe { CStr::from_ptr(rule_host) }.to_str() {
            Ok(rule) => rule,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };
        if domain::host_matches(host, rule) { 1 } else { 0 }
    }))
    .unwrap_or(ERR_PANIC as i32)
}

/// Clamp a monotonic elapsed-time sample, protecting accounting from suspend or
/// debugger pauses. A missing prior sample accounts for zero elapsed time.
pub fn capped_elapsed_ms(previous_ms: Option<u64>, now_ms: u64, maximum_ms: u64) -> u64 {
    previous_ms
        .map(|previous| now_ms.saturating_sub(previous).min(maximum_ms))
        .unwrap_or(0)
}

/// C ABI wrapper for [`capped_elapsed_ms`].
#[no_mangle]
pub extern "C" fn dw_capped_elapsed_ms(
    has_previous: u8,
    previous_ms: u64,
    now_ms: u64,
    maximum_ms: u64,
) -> u64 {
    let previous = if has_previous == 0 {
        None
    } else {
        Some(previous_ms)
    };
    capped_elapsed_ms(previous, now_ms, maximum_ms)
}

/// Select a tracking-session transition for a fresh foreground sample.
///
/// The return code is a stable `tracking::TransitionAction` discriminant.
#[no_mangle]
pub extern "C" fn dw_decide_tracking_transition(
    has_current_app: u8,
    same_process: u8,
    idle_changed: u8,
    title_changed: u8,
    fullscreen_game: u8,
    session_duration_ms: u64,
) -> u32 {
    tracking::select_transition(
        has_current_app != 0,
        same_process != 0,
        idle_changed != 0,
        title_changed != 0,
        fullscreen_game != 0,
        session_duration_ms,
    ) as u32
}

/// Select the most specific enabled website rule for normalized host/path data.
///
/// Returns `0` for allow, `1` for block, or a negative error code. On success,
/// `selected_index` receives the zero-based input index, or `-1` when the default
/// action applies. A null rule pointer is accepted only when `rule_count` is zero.
///
/// # Safety
/// The URL inputs and non-null rule strings must be readable NUL-terminated
/// UTF-8. The rule array must contain `rule_count` valid `UrlRuleView` records,
/// and `selected_index` must point to a writable `isize`.
#[no_mangle]
pub unsafe extern "C" fn dw_select_url_rule(
    url_host: *const c_char,
    url_path: *const c_char,
    default_action: u8,
    rules: *const url_rules::UrlRuleView,
    rule_count: usize,
    selected_index: *mut isize,
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if url_host.is_null() || url_path.is_null() || selected_index.is_null() {
            return ERR_NULL_POINTER as i32;
        }
        if rule_count > 4_096 || !matches!(default_action, 0 | 1) {
            return ERR_INVALID_ARGUMENT;
        }
        if rule_count > 0 && rules.is_null() {
            return ERR_NULL_POINTER as i32;
        }

        // SAFETY: readable, NUL-terminated URL inputs are part of this function's contract.
        let url_host = match unsafe { CStr::from_ptr(url_host) }.to_str() {
            Ok(value) => value,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };
        // SAFETY: readable, NUL-terminated URL inputs are part of this function's contract.
        let url_path = match unsafe { CStr::from_ptr(url_path) }.to_str() {
            Ok(value) => value,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };

        let rule_views: &[url_rules::UrlRuleView] = if rule_count == 0 {
            &[]
        } else {
            // SAFETY: the caller promises a valid array containing `rule_count` views.
            unsafe { std::slice::from_raw_parts(rules, rule_count) }
        };
        let mut parsed_rules = Vec::with_capacity(rule_count);
        for view in rule_views {
            if view.host.is_null() || view.path.is_null() || !matches!(view.action, 0 | 1) {
                return ERR_INVALID_ARGUMENT;
            }
            // SAFETY: each rule string pointer is valid through this call by contract.
            let host = match unsafe { CStr::from_ptr(view.host) }.to_str() {
                Ok(value) => value,
                Err(_) => return ERR_INVALID_UTF8 as i32,
            };
            // SAFETY: each rule string pointer is valid through this call by contract.
            let path = match unsafe { CStr::from_ptr(view.path) }.to_str() {
                Ok(value) => value,
                Err(_) => return ERR_INVALID_UTF8 as i32,
            };
            parsed_rules.push(url_rules::RuleRef {
                host,
                path,
                action: view.action,
                enabled: view.enabled != 0,
            });
        }

        let (action, index) =
            url_rules::select_rule(url_host, url_path, default_action, &parsed_rules);
        // SAFETY: `selected_index` is required to point to writable storage.
        unsafe { selected_index.write(index.map(|value| value as isize).unwrap_or(-1)) };
        action as i32
    }))
    .unwrap_or(ERR_PANIC as i32)
}

/// Categorize a process and return compact reason data through output pointers.
///
/// Returns `0` on success or a negative error code. Reason kinds are documented
/// by `categorizer`; an empty reason value is still written as a C string.
///
/// # Safety
/// Both inputs must point to readable NUL-terminated UTF-8 strings. The category
/// and reason-kind pointers must be writable `u32` values. The reason buffer
/// must be writable for `reason_value_capacity` bytes.
#[no_mangle]
pub unsafe extern "C" fn dw_categorize_process(
    process_name: *const c_char,
    exe_path: *const c_char,
    category_output: *mut u32,
    reason_kind_output: *mut u32,
    reason_value_output: *mut c_char,
    reason_value_capacity: usize,
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if process_name.is_null()
            || exe_path.is_null()
            || category_output.is_null()
            || reason_kind_output.is_null()
            || reason_value_output.is_null()
        {
            return ERR_NULL_POINTER as i32;
        }

        // SAFETY: readable NUL-terminated inputs are part of this function's contract.
        let process_name = match unsafe { CStr::from_ptr(process_name) }.to_str() {
            Ok(value) => value,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };
        // SAFETY: readable NUL-terminated inputs are part of this function's contract.
        let exe_path = match unsafe { CStr::from_ptr(exe_path) }.to_str() {
            Ok(value) => value,
            Err(_) => return ERR_INVALID_UTF8 as i32,
        };

        let result = categorizer::categorize_process(process_name, exe_path);
        // SAFETY: writable output buffer and its capacity are part of the contract.
        let written = unsafe {
            write_c_string(
                reason_value_output,
                reason_value_capacity,
                &result.reason_value,
            )
        };
        if written < 0 {
            return written as i32;
        }

        // SAFETY: both output pointers are required to point to writable u32 values.
        unsafe {
            category_output.write(result.category);
            reason_kind_output.write(result.reason_kind);
        }
        0
    }))
    .unwrap_or(ERR_PANIC as i32)
}

unsafe fn write_c_string(output: *mut c_char, capacity: usize, value: &str) -> isize {
    if value.len().saturating_add(1) > capacity {
        return ERR_OUTPUT_TOO_SMALL;
    }
    // SAFETY: caller promises a writable buffer of `capacity` bytes; the size
    // check above ensures the copy and trailing NUL fit in that buffer.
    unsafe {
        ptr::copy_nonoverlapping(value.as_ptr(), output.cast::<u8>(), value.len());
        output.add(value.len()).write(0);
    }
    value.len() as isize
}

#[cfg(test)]
mod tests {
    use super::{capped_elapsed_ms, dw_core_abi_version};

    #[test]
    fn elapsed_accounting_is_saturating_and_bounded() {
        assert_eq!(capped_elapsed_ms(None, 100, 5_000), 0);
        assert_eq!(capped_elapsed_ms(Some(100), 250, 5_000), 150);
        assert_eq!(capped_elapsed_ms(Some(250), 100, 5_000), 0);
        assert_eq!(capped_elapsed_ms(Some(0), 9_000, 5_000), 5_000);
    }

    #[test]
    fn exposes_expected_abi_version() {
        assert_eq!(dw_core_abi_version(), 4);
    }
}

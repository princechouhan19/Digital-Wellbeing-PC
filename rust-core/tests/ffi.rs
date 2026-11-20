use std::ffi::{c_char, CStr, CString};
use std::ptr;

use digital_wellbeing_core::{
    dw_categorize_process, dw_core_abi_version, dw_decide_tracking_transition,
    dw_domain_matches, dw_extract_domain_from_title, dw_normalize_domain, dw_select_url_rule,
};
use digital_wellbeing_core::url_rules::UrlRuleView;

#[test]
fn domain_functions_obey_the_c_abi_contract() {
    assert_eq!(dw_core_abi_version(), 4);

    let title = CString::new("GitHub - Google Chrome").unwrap();
    let mut output = [0 as c_char; 512];
    // SAFETY: both C strings are NUL-terminated and output is writable.
    let written = unsafe {
        dw_extract_domain_from_title(title.as_ptr(), output.as_mut_ptr(), output.len())
    };
    assert_eq!(written, "github.com".len() as isize);
    // SAFETY: the function writes a NUL-terminated string when it succeeds.
    let result = unsafe { CStr::from_ptr(output.as_ptr()) };
    assert_eq!(result.to_str().unwrap(), "github.com");

    let raw_domain = CString::new("HTTPS://WWW.YouTube.com/watch?v=1").unwrap();
    // SAFETY: both C strings are NUL-terminated and output is writable.
    let written = unsafe {
        dw_normalize_domain(raw_domain.as_ptr(), output.as_mut_ptr(), output.len())
    };
    assert_eq!(written, "youtube.com".len() as isize);
    // SAFETY: the function writes a NUL-terminated string when it succeeds.
    let result = unsafe { CStr::from_ptr(output.as_ptr()) };
    assert_eq!(result.to_str().unwrap(), "youtube.com");

    let unicode_domain = CString::new("ÄPFEL.de").unwrap();
    // SAFETY: input and output buffers remain valid and large enough for UTF-8 output.
    let written = unsafe {
        dw_normalize_domain(
            unicode_domain.as_ptr(),
            output.as_mut_ptr(),
            output.len(),
        )
    };
    assert_eq!(written, "äpfel.de".len() as isize);
    // SAFETY: successful normalization writes a NUL-terminated UTF-8 string.
    let result = unsafe { CStr::from_ptr(output.as_ptr()) };
    assert_eq!(result.to_str().unwrap(), "äpfel.de");

    let host = CString::new("www.reddit.com").unwrap();
    let rule = CString::new("reddit.com").unwrap();
    // SAFETY: both arguments are valid NUL-terminated UTF-8 strings.
    assert_eq!(unsafe { dw_domain_matches(host.as_ptr(), rule.as_ptr()) }, 1);
}

#[test]
fn ffi_reports_invalid_inputs_without_writing_past_the_buffer() {
    let title = CString::new("A known example.com page").unwrap();
    let mut too_small = [0 as c_char; 2];
    // SAFETY: input is valid; the output buffer is valid but intentionally too small.
    assert_eq!(
        unsafe {
            dw_extract_domain_from_title(
                title.as_ptr(),
                too_small.as_mut_ptr(),
                too_small.len(),
            )
        },
        -3
    );

    // SAFETY: null is explicitly accepted and rejected before dereferencing.
    assert_eq!(
        unsafe { dw_extract_domain_from_title(ptr::null(), too_small.as_mut_ptr(), too_small.len()) },
        -1
    );

    let invalid_utf8 = [0xff_u8, 0];
    // SAFETY: this is a readable NUL-terminated byte string, intentionally not UTF-8.
    assert_eq!(
        unsafe {
            dw_extract_domain_from_title(
                invalid_utf8.as_ptr().cast(),
                too_small.as_mut_ptr(),
                too_small.len(),
            )
        },
        -2
    );
}

#[test]
fn ffi_exposes_tracking_transition_policy() {
    assert_eq!(dw_decide_tracking_transition(1, 1, 0, 1, 0, 1_999), 6);
    assert_eq!(dw_decide_tracking_transition(1, 1, 0, 1, 0, 2_000), 5);
    assert_eq!(dw_decide_tracking_transition(1, 1, 0, 1, 1, 5_000), 4);
}

#[test]
fn ffi_exposes_url_rule_selection() {
    let host = CString::new("www.example.com").unwrap();
    let path = CString::new("/account/settings").unwrap();
    let broad_host = CString::new("example.com").unwrap();
    let root_path = CString::new("/").unwrap();
    let private_host = CString::new("example.com").unwrap();
    let private_path = CString::new("/account").unwrap();
    let rules = [
        UrlRuleView {
            host: broad_host.as_ptr(),
            path: root_path.as_ptr(),
            action: 1,
            enabled: 1,
        },
        UrlRuleView {
            host: private_host.as_ptr(),
            path: private_path.as_ptr(),
            action: 0,
            enabled: 1,
        },
    ];
    let mut selected_index = -99_isize;
    // SAFETY: all input C strings and the rule array remain alive and readable for this call.
    let action = unsafe {
        dw_select_url_rule(
            host.as_ptr(),
            path.as_ptr(),
            0,
            rules.as_ptr(),
            rules.len(),
            &mut selected_index,
        )
    };
    assert_eq!(action, 0);
    assert_eq!(selected_index, 1);

    selected_index = -99;
    // SAFETY: pointers are valid; a null rule array is allowed with a zero count.
    let action = unsafe {
        dw_select_url_rule(
            host.as_ptr(),
            path.as_ptr(),
            1,
            ptr::null(),
            0,
            &mut selected_index,
        )
    };
    assert_eq!(action, 1);
    assert_eq!(selected_index, -1);
}

#[test]
fn ffi_rejects_invalid_url_rule_arguments() {
    let host = CString::new("example.com").unwrap();
    let path = CString::new("/").unwrap();
    let mut selected_index = 23_isize;

    // SAFETY: valid URL strings/output are provided; invalid action is rejected before rule access.
    assert_eq!(
        unsafe {
            dw_select_url_rule(
                host.as_ptr(),
                path.as_ptr(),
                2,
                ptr::null(),
                0,
                &mut selected_index,
            )
        },
        -5
    );
    assert_eq!(selected_index, 23);

    // SAFETY: the null rule array is rejected when the nonzero count is checked.
    assert_eq!(
        unsafe {
            dw_select_url_rule(
                host.as_ptr(),
                path.as_ptr(),
                0,
                ptr::null(),
                1,
                &mut selected_index,
            )
        },
        -1
    );

    let invalid_rule = [UrlRuleView {
        host: ptr::null(),
        path: path.as_ptr(),
        action: 0,
        enabled: 1,
    }];
    // SAFETY: the function rejects the null host pointer before dereferencing it.
    assert_eq!(
        unsafe {
            dw_select_url_rule(
                host.as_ptr(),
                path.as_ptr(),
                0,
                invalid_rule.as_ptr(),
                invalid_rule.len(),
                &mut selected_index,
            )
        },
        -5
    );
}

#[test]
fn ffi_returns_process_category_and_reason_descriptor() {
    let name = CString::new("RiotClientServices.exe").unwrap();
    let path = CString::new("").unwrap();
    let mut category = 0_u32;
    let mut reason_kind = 0_u32;
    let mut reason_value = [0 as c_char; 512];
    // SAFETY: inputs are NUL-terminated and all outputs are writable.
    let status = unsafe {
        dw_categorize_process(
            name.as_ptr(),
            path.as_ptr(),
            &mut category,
            &mut reason_kind,
            reason_value.as_mut_ptr(),
            reason_value.len(),
        )
    };
    assert_eq!(status, 0);
    assert_eq!(category, 3);
    assert_eq!(reason_kind, 2);
    // SAFETY: the function writes a NUL-terminated reason value on success.
    let reason_value = unsafe { CStr::from_ptr(reason_value.as_ptr()) };
    assert_eq!(reason_value.to_str().unwrap(), "riotclientservices");
}

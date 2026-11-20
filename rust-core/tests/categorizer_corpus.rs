use digital_wellbeing_core::categorizer::categorize_process;

fn category_name(code: u32) -> &'static str {
    match code {
        0 => "Other",
        1 => "Browser",
        2 => "Programming",
        3 => "Gaming",
        4 => "Communication",
        5 => "Productivity",
        6 => "Entertainment",
        7 => "System",
        8 => "Utilities",
        9 => "Education",
        10 => "Social",
        _ => panic!("unknown category code {code}"),
    }
}

fn reason_kind(name: &str) -> u32 {
    match name {
        "none" => 0,
        "path" => 1,
        "launcher" => 2,
        "game" => 3,
        _ => panic!("unknown reason kind {name:?}"),
    }
}

#[test]
fn matches_shared_python_categorizer_corpus() {
    for line in include_str!("fixtures/categorizer_cases.tsv").lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        assert_eq!(fields.len(), 5, "fixture rows contain five tab-separated fields");
        let expected_reason_value = if fields[4] == "-" { "" } else { fields[4] };
        let result = categorize_process(fields[0], fields[1]);
        assert_eq!(category_name(result.category), fields[2], "for {line:?}");
        assert_eq!(result.reason_kind, reason_kind(fields[3]), "for {line:?}");
        assert_eq!(result.reason_value, expected_reason_value, "for {line:?}");
    }
}

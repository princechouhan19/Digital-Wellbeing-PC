use digital_wellbeing_core::tracking::select_transition;

#[test]
fn matches_shared_python_rust_transition_corpus() {
    for line in include_str!("fixtures/tracking_transition_cases.tsv").lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        assert_eq!(fields.len(), 7, "fixture rows contain seven tab-separated fields");
        let flag = |index: usize| fields[index] == "1";
        let duration_ms = fields[5]
            .parse::<u64>()
            .expect("duration is an unsigned millisecond count");
        let expected = fields[6]
            .parse::<u32>()
            .expect("expected transition is a numeric action code");
        let actual = select_transition(
            flag(0),
            flag(1),
            flag(2),
            flag(3),
            flag(4),
            duration_ms,
        ) as u32;
        assert_eq!(actual, expected, "unexpected transition for {line:?}");
    }
}

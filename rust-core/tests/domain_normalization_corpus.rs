use digital_wellbeing_core::domain::normalize_domain;

#[test]
fn normalizes_shared_domain_input_corpus() {
    for line in include_str!("fixtures/domain_normalization_cases.tsv").lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (raw, expected) = line
            .split_once('\t')
            .expect("fixture rows contain an input and expected output");
        let raw = if raw == "-" { "" } else { raw };
        let expected = if expected == "-" { "" } else { expected };
        assert_eq!(normalize_domain(raw), expected, "for input {raw:?}");
    }
}

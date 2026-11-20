use digital_wellbeing_core::domain::extract_domain_from_title;

#[test]
fn matches_shared_python_rust_conformance_corpus() {
    for line in include_str!("fixtures/domain_title_cases.tsv").lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (title, expected) = line
            .split_once('\t')
            .expect("fixture rows contain a title and expected value separated by a tab");
        let expected = if expected == "-" { "" } else { expected };
        assert_eq!(
            extract_domain_from_title(title),
            expected,
            "unexpected result for browser title {title:?}"
        );
    }
}

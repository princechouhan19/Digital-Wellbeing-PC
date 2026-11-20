use digital_wellbeing_core::url_rules::{select_rule, RuleRef, ACTION_ALLOW, ACTION_BLOCK};

fn action_code(action: &str) -> u8 {
    match action {
        "allow" => ACTION_ALLOW,
        "block" => ACTION_BLOCK,
        _ => panic!("unknown URL-rule action {action:?}"),
    }
}

#[test]
fn matches_shared_python_url_rule_corpus() {
    for line in include_str!("fixtures/url_rule_cases.tsv").lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        assert_eq!(fields.len(), 6, "fixture rows contain six tab-separated fields");
        let default_action = action_code(fields[2]);
        let rules = if fields[3] == "-" {
            Vec::new()
        } else {
            fields[3]
                .split(';')
                .map(|serialized| {
                    let parts: Vec<&str> = serialized.split(',').collect();
                    assert_eq!(parts.len(), 4, "malformed rule in {line:?}");
                    RuleRef {
                        host: parts[2],
                        path: if parts[3] == "-" { "" } else { parts[3] },
                        action: action_code(parts[0]),
                        enabled: parts[1] == "1",
                    }
                })
                .collect::<Vec<_>>()
        };
        let (actual_action, actual_index) =
            select_rule(fields[0], fields[1], default_action, &rules);
        let expected_index = fields[5]
            .parse::<isize>()
            .expect("expected index is a signed integer");
        assert_eq!(actual_action, action_code(fields[4]), "for {line:?}");
        assert_eq!(actual_index.map(|index| index as isize).unwrap_or(-1), expected_index, "for {line:?}");
    }
}

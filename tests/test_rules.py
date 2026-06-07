from pdf_guard.rules import DEFAULT_RULES, find_sensitive_values


def test_default_rules_find_common_sensitive_values():
    text = "手机 13812345678 身份证 110101199001011234 邮箱 demo@example.com"
    hits = find_sensitive_values(text, [DEFAULT_RULES["mobile"], DEFAULT_RULES["id_card"], DEFAULT_RULES["email"]])

    assert hits["mobile"] == ["13812345678"]
    assert hits["id_card"] == ["110101199001011234"]
    assert hits["email"] == ["demo@example.com"]


def test_keywords_are_exact_candidates():
    hits = find_sensitive_values("项目 Alpha 需要脱敏", [], ["Alpha", "Beta"])
    assert hits == {"keyword": ["Alpha"]}


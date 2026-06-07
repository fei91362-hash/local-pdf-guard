from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: re.Pattern[str]


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


DEFAULT_RULES: dict[str, Rule] = {
    "mobile": Rule("mobile", _compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    "id_card": Rule("id_card", _compile(r"(?<!\d)\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
    "email": Rule("email", _compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    "bank_card": Rule("bank_card", _compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    "uscc": Rule("uscc", _compile(r"\b[0-9A-Z]{18}\b")),
}


def selected_rules(
    redact_mobile: bool = False,
    redact_id_card: bool = False,
    redact_email: bool = False,
    redact_bank_card: bool = False,
    redact_uscc: bool = False,
) -> list[Rule]:
    rules: list[Rule] = []
    if redact_mobile:
        rules.append(DEFAULT_RULES["mobile"])
    if redact_id_card:
        rules.append(DEFAULT_RULES["id_card"])
    if redact_email:
        rules.append(DEFAULT_RULES["email"])
    if redact_bank_card:
        rules.append(DEFAULT_RULES["bank_card"])
    if redact_uscc:
        rules.append(DEFAULT_RULES["uscc"])
    return rules


def find_sensitive_values(text: str, rules: Iterable[Rule], keywords: Iterable[str] = ()) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for rule in rules:
        values = sorted({m.group(0).strip() for m in rule.pattern.finditer(text) if m.group(0).strip()})
        if values:
            hits[rule.category] = values

    keyword_values = sorted({k.strip() for k in keywords if k.strip() and k.strip() in text})
    if keyword_values:
        hits["keyword"] = keyword_values
    return hits


"""Drive search queries are string literals; names with quotes must be escaped, not passed through."""
from qa_bug_logger.evidence import drive_query_literal


def test_apostrophe_is_escaped():
    assert drive_query_literal("O'Brien's app") == "O\\'Brien\\'s app"


def test_backslash_is_escaped_before_quotes():
    assert drive_query_literal("a\\'b") == "a\\\\\\'b"


def test_injection_attempt_stays_inside_the_literal():
    name = "x' or name contains '"
    q = f"name='{drive_query_literal(name)}'"
    # every quote inside the value is escaped, so the literal still closes only at the end
    assert q.count("\\'") == 2 and q.endswith("'")

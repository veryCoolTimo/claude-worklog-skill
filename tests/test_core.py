from worklog.core import merge_text


def test_merge_text_skips_exact_duplicate():
    assert merge_text("did X", "did X") == "did X"
    assert merge_text("did X", "did Y") == "did X; did Y"
    assert merge_text("", "did X") == "did X"
    assert merge_text("a; b", "b") == "a; b"

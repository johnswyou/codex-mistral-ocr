import pytest

from codex_mistral_ocr.page_ranges import PageRangeError, human_pages_to_display, parse_human_pages


def test_parse_human_pages_none_and_blank():
    assert parse_human_pages(None) is None
    assert parse_human_pages("") is None
    assert parse_human_pages("   ") is None


def test_parse_human_pages_single_range_and_list():
    assert parse_human_pages("1") == [0]
    assert parse_human_pages("1,3-5") == [0, 2, 3, 4]
    assert parse_human_pages("2:4") == [1, 2, 3]
    assert human_pages_to_display("1,3-4") == "1,3,4"


@pytest.mark.parametrize("value", ["0", "3-1", "abc", "1,,x", "-2"])
def test_parse_human_pages_rejects_invalid_values(value):
    with pytest.raises(PageRangeError):
        parse_human_pages(value)

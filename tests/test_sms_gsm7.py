import pytest

from src.sms_handler import MAX_SMS_LENGTH, gsm7_safe, is_gsm7, split_response_for_sms


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello, this is marty.", True),
        ("café", True),  # é is GSM-7
        ("hi 👋", False),  # emoji
        ("1234567890!@#?", True),
        ("smart quotes: \u201chello\u201d", False),  # curly quotes are not GSM-7
        ("ümlaut ü", True),  # ü is GSM-7
        ("accented à", True),  # à is GSM-7
        ("greek Δ", True),  # Δ is GSM-7
        ("chinese 汉字", False),
        ("{}[]|~^€", True),  # extended GSM-7 chars
    ],
)
def test_is_gsm7(text, expected):
    assert is_gsm7(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello, this is marty.", "hello, this is marty."),
        ("café", "café"),  # é is GSM-7, no replacement needed
        ("hi 👋", "hi ?"),
        ("smart quotes: \u201chello\u201d", "smart quotes: ?hello?"),
        ("ümlaut ü", "ümlaut ü"),  # ü is GSM-7, no replacement needed
        ("accented à", "accented à"),  # à is GSM-7, no replacement needed
        ("greek Δ", "greek Δ"),  # Δ is GSM-7, no replacement needed
        ("chinese 汉字", "chinese ??"),
        ("{}[]|~^€", "{}[]|~^€"),  # extended GSM-7 chars, no replacement needed
    ],
)
def test_gsm7_safe(text, expected):
    assert gsm7_safe(text) == expected


def test_split_response_for_sms_basic():
    # Fits in one SMS
    msg = "hello, this is marty. what do you want to read?"
    result = split_response_for_sms(msg)
    assert result == [msg]
    assert all(len(chunk) <= MAX_SMS_LENGTH for chunk in result)


def test_split_response_for_sms_long():
    # Multiple sentences, should pack as many as possible per SMS
    s = "this is sentence one. this is sentence two! this is sentence three? " * 10
    result = split_response_for_sms(s)
    assert all(len(chunk) <= MAX_SMS_LENGTH for chunk in result)
    # Should not split mid-sentence unless needed
    for chunk in result:
        assert chunk.endswith((".", "!", "?")) or chunk == result[-1]


def test_split_response_for_sms_long_sentence():
    # Single sentence longer than MAX_SMS_LENGTH
    long_sentence = "a" * (MAX_SMS_LENGTH + 20) + "."
    result = split_response_for_sms(long_sentence)
    assert all(len(chunk) <= MAX_SMS_LENGTH for chunk in result)
    assert sum(len(chunk) for chunk in result) >= len(long_sentence)


def test_split_response_for_sms_empty():
    assert split_response_for_sms("") == []
    assert split_response_for_sms("   ") == []


def test_split_response_for_sms_word_split():
    # Sentence with a single long word
    long_word = "x" * (MAX_SMS_LENGTH + 10)
    result = split_response_for_sms(long_word)
    assert all(len(chunk) <= MAX_SMS_LENGTH for chunk in result)
    assert sum(len(chunk) for chunk in result) >= len(long_word)

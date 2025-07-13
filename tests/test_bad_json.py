import pytest
from backend.json_utils import safe_load, BadJSON


def test_valid_json():
    """Тест корректного JSON"""
    valid_json = '{"foo": 1, "bar": "test"}'
    result = safe_load(valid_json)
    assert result == {"foo": 1, "bar": "test"}


def test_json_with_text_wrapper():
    """Тест JSON внутри текста"""
    wrapped_json = 'Some text before {"foo": 1, "bar": "test"} and after'
    result = safe_load(wrapped_json)
    assert result == {"foo": 1, "bar": "test"}


def test_bad_json_raises_exception():
    """Тест что плохой JSON вызывает исключение"""
    bad = "bla-bla {\"foo\":1, } trailing"
    with pytest.raises(BadJSON):
        safe_load(bad)


def test_bad_json_exception_contains_info():
    """Тест что исключение содержит полезную информацию"""
    bad = "completely invalid json string"
    with pytest.raises(BadJSON) as exc_info:
        safe_load(bad)
    
    # Проверяем что в сообщении есть часть оригинального текста
    assert "completely invalid" in str(exc_info.value)


def test_complex_json_extraction():
    """Тест извлечения сложного JSON из текста"""
    complex_text = '''
    Here is some explanation.
    
    {"need_clarify": true, "clarify": "Please provide more details", "need_escalate": false, "draft": "Initial response"}
    
    Additional notes.
    '''
    result = safe_load(complex_text)
    expected = {
        "need_clarify": True,
        "clarify": "Please provide more details", 
        "need_escalate": False,
        "draft": "Initial response"
    }
    assert result == expected


def test_empty_string():
    """Тест пустой строки"""
    with pytest.raises(BadJSON):
        safe_load("")


def test_no_json_in_text():
    """Тест текста без JSON"""
    with pytest.raises(BadJSON):
        safe_load("This is just plain text without any JSON structure")

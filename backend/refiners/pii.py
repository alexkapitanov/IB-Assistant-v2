import re
from typing import Tuple

EMAIL = re.compile(r'(?i)([A-Z0-9._%+-]{1,64})@([A-Z0-9.-]{1,255}\.[A-Z]{2,24})')
# Дефис внутри символьного класса должен быть экранирован; используем устойчивую маску для RU-телефонов (+7/8)
# Пример: +7 (999) 123-45-67
PHONE = re.compile(r'(?<!\d)(?:\+7|8)[\s\-\(\)]*(?:\d[\s\-\(\)]*){10}(?!\d)')
# РФ паспорт: 10 цифр, иногда через пробелы: "12 34 567890" или "1234567890"
RU_PASSPORT = re.compile(r'(?<!\d)(\d{2}\s?\d{2}\s?\d{6})(?!\d)')
# СНИЛС: 000-000-000 00
SNILS = re.compile(r'(?<!\d)(\d{3}-\d{3}-\d{3}\s?\d{2})(?!\d)')
# ИНН: 10 или 12 цифр
INN = re.compile(r'(?<!\d)(\d{10}|\d{12})(?!\d)')
# Банковская карта (мягкая маска 13–19 цифр)
CARD = re.compile(r'(?<!\d)(\d[\s\-]?){13,19}\d(?!\d)')


def _mask_middle(s: str, keep_left: int = 2, keep_right: int = 2, repl: str = "*") -> str:
    if len(s) <= keep_left + keep_right:
        return repl * len(s)
    return s[:keep_left] + repl * (len(s) - keep_left - keep_right) + s[-keep_right:]


def scrub_text(text: str) -> Tuple[str, bool]:
    """
    Маскирует PII. Возвращает (scrubbed_text, changed).
    Сохраняем маркеры [¹] ссылок и markdown как есть.
    """
    changed = False

    def sub_email(m: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        local, domain = m.group(1), m.group(2)
        return _mask_middle(local, 1, 1) + '@' + domain

    def sub_generic(m: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        raw = re.sub(r'\D', '', m.group(0))  # нормализуем
        masked = _mask_middle(raw, 2, 2)
        return masked

    out = EMAIL.sub(sub_email, text)
    out = PHONE.sub(sub_generic, out)
    out = RU_PASSPORT.sub(sub_generic, out)
    out = SNILS.sub(sub_generic, out)
    out = INN.sub(sub_generic, out)
    out = CARD.sub(sub_generic, out)
    return out, changed

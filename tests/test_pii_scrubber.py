from backend.refiners.pii import scrub_text

def test_email_mask():
    t, ch = scrub_text("Почта ivan.petrov@example.com ок")
    # Проверяем первый символ локальной части email, а не первый символ всей строки
    local = t.split(" ")[-2].split("@")[0] if "@example.com" in t else t.split("@")[0]
    assert ch and "@example.com" in t and local[0].lower() == "i"


def test_ru_passport():
    t, ch = scrub_text("паспорт 12 34 567890 проверен")
    assert ch and "*" in t


def test_phone():
    t, ch = scrub_text("тел: +7 (999) 123-45-67")
    assert ch and t.count("*") > 3


def test_snils():
    t, ch = scrub_text("СНИЛС 123-456-789 00")
    assert ch


def test_card_like():
    t, ch = scrub_text("номер карты 4111 1111 1111 1111")
    assert ch

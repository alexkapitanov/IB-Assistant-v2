import subprocess, pathlib, sys

def test_no_4o_left():
    """Тест проверяет отсутствие запрещённой модели в кодовой базе"""
    root = pathlib.Path(__file__).resolve().parents[1]
    try:
        out = subprocess.check_output(
            ["grep", "-R", "gpt-4o", str(root), "--include=*.py", "--include=*.md", "--exclude=test_no_4o.py"], 
            stderr=subprocess.DEVNULL
        ).decode()
        # Если grep нашёл что-то, выводим ошибку
        assert out.strip() == "", f"Found forbidden model in codebase:\n{out}"
    except subprocess.CalledProcessError:
        # grep возвращает код 1 если ничего не найдено - это хорошо
        pass

def test_no_4o_mini_left():
    """Тест проверяет отсутствие запрещённой модели в кодовой базе"""
    root = pathlib.Path(__file__).resolve().parents[1]
    try:
        out = subprocess.check_output(
            ["grep", "-R", "gpt-4o-mini", str(root), "--include=*.py", "--include=*.md", "--exclude=test_no_4o.py"], 
            stderr=subprocess.DEVNULL
        ).decode()
        # Если grep нашёл что-то, выводим ошибку
        assert out.strip() == "", f"Found forbidden model in codebase:\n{out}"
    except subprocess.CalledProcessError:
        # grep возвращает код 1 если ничего не найдено - это хорошо
        pass

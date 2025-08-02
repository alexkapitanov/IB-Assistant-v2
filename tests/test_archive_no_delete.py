import types
import sqlite3
import scripts.archive_dialogs as arch
from backend import config

def test_archive_nothing_recent(tmp_path, monkeypatch):
    # Устанавливаем специфичные для теста значения
    monkeypatch.setenv("DIALOG_TTL_DAYS", "0")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    config.config.reload()

    # Подменяем S3 клиент, чтобы не делать реальных вызовов
    monkeypatch.setattr(arch.boto3, "client", lambda *a, **k: types.SimpleNamespace(upload_fileobj=lambda *a, **k: None))
    
    arch.run()  # Не должно вызывать исключений

def test_archive_one_old(tmp_path, monkeypatch):
    # Устанавливаем путь к БД для этого теста
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    config.config.reload()

    # Создаем "старый" диалог
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dialogs (id INTEGER PRIMARY KEY, date INTEGER)''')
    c.execute('''INSERT INTO dialogs (date) VALUES (strftime('%s', 'now', '-100 days'))''')
    conn.commit()
    conn.close()

    # Подменяем S3 клиент
    monkeypatch.setattr(arch.boto3, "client", lambda *a, **k: types.SimpleNamespace(upload_fileobj=lambda *a, **k: None))
    arch.run()

    # Проверяем, что диалог был удален
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM dialogs''')
    count = c.fetchone()[0]
    conn.close()
    assert count == 0

def test_archive_one_old_no_delete(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("ARCHIVE_DELETE_AFTER_BACKUP", "false")
    config.config.reload()

    # Создаем "старый" диалог
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dialogs (id INTEGER PRIMARY KEY, date INTEGER)''')
    c.execute('''INSERT INTO dialogs (date) VALUES (strftime('%s', 'now', '-100 days'))''')
    conn.commit()
    conn.close()

    # Подменяем S3 клиент
    monkeypatch.setattr(arch.boto3, "client", lambda *a, **k: types.SimpleNamespace(upload_fileobj=lambda *a, **k: None))
    arch.run()

    # Проверяем, что диалог не был удален
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM dialogs''')
    count = c.fetchone()[0]
    conn.close()
    assert count == 1

import pytest
import uuid
import json
import sqlite3
from backend.chat_db import log_message, get_current_thread_messages, save_dialog_full, DB_PATH, _conn

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    """Очищает таблицы dialog_log и chatlog перед каждым тестом."""
    with _conn() as c:
        c.execute("DELETE FROM dialog_log")
        c.execute("DELETE FROM chatlog")
    yield
    with _conn() as c:
        c.execute("DELETE FROM dialog_log")
        c.execute("DELETE FROM chatlog")


def test_save_and_get_dialog():
    """
    Проверяет полный цикл: логирование сообщений, получение и сохранение диалога.
    """
    thread_id = str(uuid.uuid4())
    
    # 1. Логируем несколько сообщений
    log_message(thread_id, 1, "user", "Привет, как дела?")
    log_message(thread_id, 1, "assistant", "Привет! Я — большая языковая модель, у меня всё отлично.")
    log_message(thread_id, 2, "user", "Что ты умеешь?")
    log_message(thread_id, 2, "assistant", "Я умею отвечать на вопросы, искать информацию и многое другое.")

    # 2. Получаем историю диалога
    messages = get_current_thread_messages(thread_id)
    assert len(messages) == 4
    assert messages[0]['role'] == 'user'
    assert messages[-1]['content'] == "Я умею отвечать на вопросы, искать информацию и многое другое."

    # 3. Сохраняем полную ветку диалога
    save_dialog_full(thread_id, messages)

    # 4. Проверяем напрямую в БД, что запись появилась и корректна
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        res = cur.execute("SELECT body FROM dialog_log WHERE thread_id = ?", (thread_id,)).fetchone()
        
        assert res is not None, "Запись в dialog_log не найдена!"
        
        saved_body = json.loads(res[0])
        assert isinstance(saved_body, list)
        assert len(saved_body) == 4
        assert saved_body == messages

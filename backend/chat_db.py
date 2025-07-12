import sqlite3, contextlib, os, pathlib

# Путь к базе данных внутри volume
DB_PATH = pathlib.Path("/data/chatlog.db")
# Создаем директорию для хранения базы, если отсутствует
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Инициализация таблицы chatlog
with sqlite3.connect(DB_PATH) as c:
    c.execute("""CREATE TABLE IF NOT EXISTS chatlog(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        turn_index INTEGER,
        role TEXT,
        content TEXT,
        model TEXT,
        latency_ms INTEGER,
        intent TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

@contextlib.contextmanager
def _conn():
    """Контекстный менеджер для подключения к базе данных"""
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        yield c

def log_message(thread, turn, role, content,
                model=None, latency_ms=None, intent=None):
    """Логирование сообщения в таблицу chatlog"""
    with _conn() as c:
        c.execute(
            """INSERT INTO chatlog(thread_id,turn_index,role,content,
                     model,latency_ms,intent) VALUES (?,?,?,?,?,?,?)""",
            (thread, turn, role, content, model, latency_ms, intent)
        )

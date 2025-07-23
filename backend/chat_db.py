import sqlite3, contextlib, os, pathlib, tempfile, json

# Путь к базе данных - используем переменную окружения для тестов
default_path = "/data/chatlog.db"
if not os.access("/data", os.W_OK):
    # Если нет доступа к /data, используем временную директорию
    default_path = os.path.join(tempfile.gettempdir(), "chatlog.db")

DB_PATH = pathlib.Path(os.getenv("DB_PATH", default_path))
# Создаем директорию для хранения базы, если отсутствует
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Инициализация таблицы chatlog и очистка для тестов
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
    c.execute("""CREATE TABLE IF NOT EXISTS dialog_log(
        thread_id TEXT PRIMARY KEY,
        body TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    # Очищаем все записи при запуске для обеспечения чистого состояния тестирования
    c.execute("DELETE FROM chatlog")
    c.execute("DELETE FROM dialog_log")

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

def log_raw(thread_id: str, turn: int, model: str, raw: str):
    """Логирование сырого ответа модели для отладки"""
    with _conn() as c:
        c.execute("""INSERT INTO chatlog(thread_id,turn_index,role,content,model)
                     VALUES (?,?,?,?,?)""",
                  (thread_id, turn, "raw", raw, model))

def get_current_thread_messages(thread_id: str) -> list[dict]:
    """Возвращает все сообщения (кроме raw) для данного thread_id."""
    with _conn() as c:
        # Выбираем только сообщения от user, assistant и system
        rows = c.execute("""SELECT role, content FROM chatlog 
                            WHERE thread_id = ? AND role != 'raw'
                            ORDER BY ts ASC""", (thread_id,)).fetchall()
        # Преобразуем каждую строку sqlite3.Row в словарь
        return [dict(row) for row in rows]

def save_dialog_full(thread_id:str, messages:list[dict]):
    """Сохраняет или заменяет полную ветку диалога в dialog_log."""
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO dialog_log(thread_id, body, ts) VALUES (?,?,CURRENT_TIMESTAMP)",
                  (thread_id, json.dumps(messages, ensure_ascii=False)))

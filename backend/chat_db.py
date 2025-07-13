import sqlite3, contextlib, os, pathlib, tempfile

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
    # Очищаем все записи при запуске для обеспечения чистого состояния тестирования
    c.execute("DELETE FROM chatlog")

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

def log_raw(thread_id, turn, model, raw):
    """Логирование сырого ответа модели для отладки"""
    with _conn() as c:
        c.execute("INSERT INTO chatlog(thread_id,turn_index,role,content,model) "
                  "VALUES (?,?,?,?,?)",
                  (thread_id, turn, "raw", raw, model))

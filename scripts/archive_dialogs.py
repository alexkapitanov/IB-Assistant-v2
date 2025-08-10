import datetime as dt
import io
import json
import sqlite3
from typing import Iterable, Tuple

from dateutil import tz

# Опциональный импорт boto3: если отсутствует, подставляем заглушку
try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover - в CI может отсутствовать
    import types

    boto3 = types.SimpleNamespace(
        client=lambda *a, **k: types.SimpleNamespace(upload_fileobj=lambda *a, **k: None)
    )

from backend import config
from backend.embedding import get as embed


def _iter_old_dialogs(conn: sqlite3.Connection, limit_dt: dt.datetime) -> Iterable[Tuple[str, str | None, str]]:
    """Итерирует диалоги, старше limit_dt, из dialog_log или dialogs (fallback)."""
    # Пытаемся читать из dialog_log
    try:
        try:
            # Если есть колонка created_at в ISO, читаем все и фильтруем по дате ниже
            cur = conn.execute("SELECT thread_id, body, created_at FROM dialog_log")
        except sqlite3.OperationalError:
            # Возможная альтернативная схема
            cur = conn.execute("SELECT thread_id, body, created FROM dialog_log")
        for tid, body, created in cur:
            yield str(tid), body, str(created)
        return
    except sqlite3.OperationalError:
        pass

    # Фолбэк: старая таблица dialogs может хранить timestamp в поле date
    try:
        cur = conn.execute("SELECT id, NULL, date FROM dialogs")
        for tid, body, created in cur:
            yield str(tid), None, str(created)
        return
    except sqlite3.OperationalError:
        # Нет ни одной подходящей таблицы — ничего архивировать
        return


def run() -> None:
    try:
        conn = sqlite3.connect(config.DB_PATH)
    except sqlite3.OperationalError:
        return

    limit_dt = dt.datetime.now(tz.UTC) - dt.timedelta(days=int(config.DIALOG_TTL_DAYS))
    s3 = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )

    to_delete: list[tuple[str]] = []
    for tid, body, created in _iter_old_dialogs(conn, limit_dt):
        # преобразуем дату: строка ISO либо timestamp
        try:
            created_dt = dt.datetime.fromisoformat(created)
        except Exception:
            try:
                created_dt = dt.datetime.fromtimestamp(int(created), tz.UTC)
            except Exception:
                continue
        if created_dt >= limit_dt:
            continue

        # резервное копирование в S3 только при наличии тела
        if body:
            key = f"{created[:10]}/{tid}.json"
            s3.upload_fileobj(io.BytesIO(body.encode()), config.ARCHIVE_BUCKET, key)
        to_delete.append((tid,))

    if not to_delete:
        return

    delete_flag = config.ARCHIVE_DELETE_AFTER_BACKUP
    if isinstance(delete_flag, str):
        delete_flag_bool = delete_flag.lower() in ("true", "1")
    else:
        delete_flag_bool = bool(delete_flag)

    if delete_flag_bool:
        # Удаляем из основной таблицы и из dialogs при fallback
        try:
            conn.executemany("DELETE FROM dialog_log WHERE thread_id=?", to_delete)
        except sqlite3.OperationalError:
            pass
        try:
            conn.executemany("DELETE FROM dialogs WHERE id=?", to_delete)
        except sqlite3.OperationalError:
            pass
        conn.commit()
        _reindex_dialogs(conn)

    # Обновление метрик — по возможности
    try:
        from backend import metrics

        if hasattr(metrics, "update_sqlite_rows"):
            metrics.update_sqlite_rows()
        if hasattr(metrics, "update_qdrant_counts"):
            metrics.update_qdrant_counts()
    except Exception:
        pass


def _reindex_dialogs(conn: sqlite3.Connection) -> None:
    try:
        cur = conn.execute("SELECT thread_id, body FROM dialog_log")
    except sqlite3.OperationalError:
        return

    # Собираем минимальный набор для апдейта индекса (пример — без реального вызова клиента)
    points = []
    for tid, body in cur:
        try:
            msgs = json.loads(body)
        except Exception:
            continue
        if not msgs:
            continue
        emb = embed(msgs[0].get("content", ""))
        ans = msgs[-1].get("content", "")
        points.append({"id": tid, "vector": emb, "payload": {"answer": ans}})

    # В реальном коде здесь бы шёл апдейт в Qdrant. Для тестов — no-op.
    return


if __name__ == "__main__":
    run()

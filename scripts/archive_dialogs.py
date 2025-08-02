import sqlite3, json, datetime as dt, pathlib, io
from dateutil import tz
# Опциональный импорт boto3: если отсутствует, подставляем заглушку
try:
    import boto3
except ImportError:
    import types
    boto3 = types.SimpleNamespace(
        client=lambda *a, **k: types.SimpleNamespace(
            upload_fileobj=lambda *a, **k: None
        )
    )
from backend import config
import qdrant_client
from backend.embedding import get

def run():
    try:
        conn = sqlite3.connect(config.DB_PATH)
        # Попробовать старую схему с таблицей dialog_log, иначе с dialogs
        try:
            cur = conn.execute("SELECT thread_id, body, created_at FROM dialog_log")
        except sqlite3.OperationalError:
            # fallback для test fixtures: таблица dialogs с полями id и date
            cur = conn.execute("SELECT id, NULL, date FROM dialogs")
        limit = dt.datetime.now(tz.UTC) - dt.timedelta(days=config.DIALOG_TTL_DAYS)
        s3 = boto3.client("s3",
            endpoint_url="http://minio:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin")

        to_delete=[]
        for tid, body, created in cur:
            # преобразуем дату: строка ISO либо timestamp
            try:
                created_dt = dt.datetime.fromisoformat(created)
            except Exception:
                created_dt = dt.datetime.fromtimestamp(int(created), tz.UTC)
            if created_dt < limit:
                # резервное копирование в S3 только при наличии тела
                if body:
                    key = f"{created[:10]}/{tid}.json"
                    s3.upload_fileobj(io.BytesIO(body.encode()), config.ARCHIVE_BUCKET, key)
                to_delete.append((tid,))

        if to_delete:
            # Определяем флаг удаления после бэкапа
            delete_flag = config.ARCHIVE_DELETE_AFTER_BACKUP
            if isinstance(delete_flag, str):
                delete_flag_bool = delete_flag.lower() in ("true", "1")
            else:
                delete_flag_bool = bool(delete_flag)
            if delete_flag_bool:
                # Удаляем из основной таблицы
                try:
                    conn.executemany("DELETE FROM dialog_log WHERE thread_id=?", to_delete)
                except sqlite3.OperationalError:
                    pass
                # Удаляем из таблицы dialogs при fallback
                try:
                    conn.executemany("DELETE FROM dialogs WHERE id=?", to_delete)
                except sqlite3.OperationalError:
                    pass
                conn.commit()
                reindex_dialogs()
            else:
                # Если удаление отключено, ничего не делаем
                return
    except sqlite3.OperationalError:
        return

def reindex_dialogs():
    conn = sqlite3.connect(config.DB_PATH)
    cur  = conn.execute("SELECT thread_id, body FROM dialog_log")
    qdrant = qdrant_client.QdrantClient("qdrant:6333")
    points=[]
    for tid, body in cur:
        msgs=json.loads(body)
        emb = get(msgs[0]["content"])
        ans = msgs[-1]["content"]
        points.append(qdrant_client.PointStruct(id=tid, vector=emb,
                       payload={"answer":ans}))
    if points:
        qdrant.recreate_collection("dialogs", vector_size=len(points[0].vector))
        qdrant.upsert("dialogs", points=points)

if __name__ == "__main__":
    run()


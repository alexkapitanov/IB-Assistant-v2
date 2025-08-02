import sqlite3
from prometheus_client import Gauge
import os
from qdrant_client import QdrantClient

SQLITE_ROWS = Gauge("sqlite_table_rows", "Rows in SQLite table", ["table"])
QDRANT_POINTS = Gauge("qdrant_collection_points", "Points in Qdrant collection", ["collection"])

DB_PATH = os.getenv("SQLITE_PATH", "/app/backend/db.sqlite3")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")

_qdrant = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")

def export_sqlite():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for table in ["dialog_log"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            SQLITE_ROWS.labels(table=table).set(count)
        conn.close()
    except Exception as e:
        print(f"SQLite export error: {e}")

def export_qdrant():
    try:
        for collection in ["docs", "dialogs"]:
            info = _qdrant.get_collection(collection)
            points = info.get("points_count", 0)
            QDRANT_POINTS.labels(collection=collection).set(points)
    except Exception as e:
        print(f"Qdrant export error: {e}")

def start_exporter():
    import threading, time
    def loop():
        while True:
            export_sqlite()
            export_qdrant()
            time.sleep(30)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

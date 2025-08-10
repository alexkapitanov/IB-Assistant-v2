import logging
import os
import sqlite3

from prometheus_client import Counter, Gauge, Histogram

STARTED = Counter("ib_req_total", "Всего запросов", ["stage"])
TIMEOUT = Counter("ib_timeout_total", "Timeouts", ["kind"])  # gc / websearch
CRITIC = Histogram("ib_critic_score", "Critic score")  # auto _bucket suffix
LAT = Histogram("ib_stage_latency_sec", "Latency по стадиям", ["stage"])
STATUS_BUS_THROUGHPUT = Counter("ib_status_bus_throughput", "Status Bus throughput", ["stage"])
EXPERT_GC_CALLS = Counter("ib_expert_gc_calls_total", "Количество вызовов Expert-GC")
SQLITE_ROWS = Gauge("sqlite_table_rows", "Rows in SQLite", ["table"])
QDRANT_POINTS = Gauge("qdrant_collection_points", "Qdrant vectors", ["collection"])

# Web cache metrics
WEB_CACHE_HIT = Counter("ib_web_cache_hit_total", "web cache hits")
WEB_CACHE_MISS = Counter("ib_web_cache_miss_total", "web cache misses")
WEB_CACHE_HIT_AFTER_WAIT = Counter("ib_web_cache_hit_after_wait_total", "wait → hit")
WEB_CACHE_STORE = Counter("ib_web_cache_store_total", "stored entries")
WEB_CACHE_STORE_NEG = Counter("ib_web_cache_store_negative_total", "stored negative")
WEB_SEARCH_LATENCY = Histogram("ib_web_search_latency_sec", "web search latency (s)")

_initialized = False

def init(port: int = 9310):
    """Initializes the Prometheus metrics server."""
    global _initialized
    print(f"🔧 metrics.init() called with port={port}")
    logging.info(f"metrics.init() called with port={port}")
    if _initialized:
        logging.info(f"Prometheus metrics server already initialized on port {port}")
        return
    try:
        from prometheus_client import start_http_server
        start_http_server(port)
        _initialized = True
        logging.info("Prometheus metrics at :%s", port)
        print(f"✅ Prometheus metrics server started on port {port}")
        
        # Инициализируем счетчики с нулевыми значениями для Grafana
        # Это создаст метрики с нулевыми значениями, которые будут показываться как горизонтальные линии
        TIMEOUT.labels(kind="gc")
        TIMEOUT.labels(kind="websearch")
        STATUS_BUS_THROUGHPUT.labels(stage="inbound")
        STATUS_BUS_THROUGHPUT.labels(stage="outbound")
        STATUS_BUS_THROUGHPUT.labels(stage="processing")
        STARTED.labels(stage="searching")
        STARTED.labels(stage="thinking")
        STARTED.labels(stage="step")
        STARTED.labels(stage="complete")
        EXPERT_GC_CALLS.inc(0)  # Инициализация с 0
        print("✅ All metrics initialized with zero values (real data only)")
        
    except Exception as e:
        print(f"❌ Failed to start metrics server: {e}")
        logging.warning(f"Failed to start metrics server on port {port}: {e}")

# update points whenever we (re)index
def update_qdrant_counts():
    """Update Qdrant collection points metrics"""
    try:
        import os

        from qdrant_client import QdrantClient
        
        qdr = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"))
        
        # Count docs collection
        try:
            docs_info = qdr.get_collection("docs")
            QDRANT_POINTS.labels(collection="docs").set(docs_info.points_count or 0)
        except Exception:
            QDRANT_POINTS.labels(collection="docs").set(0)
            
        # Count dialogs collection  
        try:
            dialogs_info = qdr.get_collection("dialogs")
            QDRANT_POINTS.labels(collection="dialogs").set(dialogs_info.points_count or 0)
        except Exception:
            QDRANT_POINTS.labels(collection="dialogs").set(0)
            
    except Exception as e:
        logging.warning(f"Failed to update Qdrant counts: {e}")

# update sqlite rows daily (or on insert)
def update_sqlite_rows():
    """Update SQLite table rows metrics"""
    try:
        db_path = os.getenv("SQLITE_DB_PATH", "/app/backend/db.sqlite3")
        if not os.path.exists(db_path):
            # Try alternative path
            db_path = "backend/db.sqlite3"
            
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if dialog_log table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dialog_log'")
            if cursor.fetchone():
                cursor.execute("SELECT count(*) FROM dialog_log")
                count = cursor.fetchone()[0]
                SQLITE_ROWS.labels(table="dialog_log").set(count)
            else:
                SQLITE_ROWS.labels(table="dialog_log").set(0)
                
            conn.close()
        else:
            SQLITE_ROWS.labels(table="dialog_log").set(0)
            
    except Exception as e:
        logging.warning(f"Failed to update SQLite rows: {e}")
        SQLITE_ROWS.labels(table="dialog_log").set(0)

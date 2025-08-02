import os
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

STARTED = Counter("ib_req_total", "Всего запросов", ["stage"])
TIMEOUT = Counter("ib_timeout_total", "Таймауты", ["kind"])  # kind=gc, websearch
CRITIC = Histogram("ib_critic_score", "Распределение скоринга Critic")
LAT = Histogram("ib_stage_latency_sec", "Latency по стадиям", ["stage"])
STATUS_BUS_THROUGHPUT = Counter("ib_status_bus_throughput", "Status Bus throughput", ["stage"])
EXPERT_GC_CALLS = Counter("ib_expert_gc_calls_total", "Количество вызовов Expert-GC")

_initialized = False

def init(port: int = None):
    """Initializes the Prometheus metrics server."""
    global _initialized
    # Порт берётся из окружения METRICS_PORT или по умолчанию 9090
    if port is None:
        try:
            port = int(os.getenv("METRICS_PORT", "9090"))
        except ValueError:
            port = 9090
    if _initialized:
        logging.info(f"Prometheus metrics server already initialized on port {port}")
        return
    try:
        start_http_server(port)
        _initialized = True
        logging.info(f"Prometheus metrics at :{port}")
    except Exception as e:
        logging.warning(f"Failed to start metrics server on port {port}: {e}")

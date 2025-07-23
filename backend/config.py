import os

# seconds; можно переопределить переменными среды/Helm-values
GC_TIMEOUT_SEC         = int(os.getenv("GC_TIMEOUT_SEC",         "300"))  # 5 мин
WEB_SEARCH_TIMEOUT_SEC = int(os.getenv("WEB_SEARCH_TIMEOUT_SEC", "20"))   # 20 с

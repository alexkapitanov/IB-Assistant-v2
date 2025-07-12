# InfoSec Assistant (multi-agent + RAG)

* FastAPI backend, React frontend.
* AutoGen GroupChat: Router (4.1-mini) ➜ Planner (4.1) ➜ ExpertGC (gpt-4.1).
* Redis — слоты, SQLite — полный лог, Qdrant — RAG, MinIO — файлы.

## Quick start
```bash
docker-compose up --build
```
### Архивирование диалогов

* Храним чаты в SQLite ≤ DIALOG_TTL_DAYS (деф. 90).
* Ночью архивный скрипт выгружает JSON в MinIO `ib-assistant-archive/YYYY-MM-DD/*.json` и удаляет записи из БД.
* После архивирования коллекция `dialogs` пересоздаётся и наполняется актуальными точками.
* Переменные:
    - DIALOG_TTL_DAYS      (days, default 90)
    - ARCHIVE_BUCKET       (s3-bucket, default ib-assistant-archive)
### Инструмент `web_search`
* Асинхронный вызов OpenAI Browser-tool.
* Таймаут задаётся `WEB_SEARCH_TIMEOUT_SEC` (по умолчанию 20 с).
* При срабатывании таймаута Search-агент возвращает строку **TIMEOUT**,
  Critic снижает уверенность → Expert-GC переходит к fallback-циклу.

### Live-статусы

* Каждый узел публикует progress в Redis `status_bus`.
* Gateway транслирует события в WebSocket/gRPC.
* Фронт показывает строку «Ассистент ищет…», «Шаг 2/4» и др.
* Канонические stage-метки: thinking | searching | web-search | step N/M | generating | done | timeout
# InfoSec Assistant (multi-agent + RAG)

* FastAPI backend, React frontend.
* Упрощенная архитектура: Dialog-Manager ➜ Planner (gpt-4.1) ➜ ExpertGC (gpt-4.1).
* Redis — слоты, SQLite — полный лог, Qdrant — RAG, MinIO — файлы.

## Область знаний

**Ассистент обучен отвечать только на вопросы по информационной безопасности —  
DLP, SIEM, SOC, стандарты, нормативы и уязвимости.**  
Если спросить о чём-то вне этой области, он честно скажет, что данных нет.

## Обязательные переменные окружения

### 🔑 Обязательные переменные
```bash
OPENAI_API_KEY=sk-***        # без него ассистент вернёт ошибку
```

### 📝 Рекомендуемые:
- `REDIS_URL` - URL для подключения к Redis (по умолчанию: redis://localhost:6379)
- `QDRANT_URL` - URL для подключения к Qdrant (по умолчанию: http://localhost:6333)

Создайте файл `.env` в корне проекта:
```bash
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

**⚠️ Обязательные шаги для запуска:**

1. **Создайте файл `.env`** в корне проекта с вашим OpenAI API ключом
2. **Для тестирования без API ключа** используйте `OPENAI_API_KEY=stub`
3. **Для разработки** убедитесь, что все сервисы запущены: Redis, Qdrant, MinIO
4. **При ошибках WebSocket** проверьте логи: `docker-compose logs backend`

## Quick start
```bash
docker-compose up --build
```

### Первая индексация

```bash
docker compose exec backend \
  python scripts/index_files.py --reindex
```

### Индексация / переиндексация документов

```bash
# Загрузили PDF вручную в MinIO консоль → запускаем reindex
docker compose exec backend python scripts/index_files.py --reindex

# Или локальные файлы
docker compose exec backend \
   python scripts/index_files.py --paths ib-docs/questionnaires/*.pdf

# Кастомный bucket и prefix
docker compose exec backend \
   python scripts/index_files.py --paths /path/to/files/*.pdf custom-bucket custom-prefix/

# Проверить содержимое MinIO
docker compose exec backend python -c "
from minio import Minio
mc = Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
for obj in mc.list_objects('ib-docs', recursive=True):
    print(f'{obj.object_name} ({obj.size} bytes)')
"
```

## Архитектура

User ─┐
      │  WebSocket / gRPC
      ▼
┌─────────────────────────── Gateway (FastAPI + grpclib) ───────────────────────────┐
│ rate-limit • /metrics (Prom) • status_bus → WS                                    │
└─────────────────────────────────────┬──────────────────────────────────────────────┘
                                      ▼
╔═════════════════════  DIALOG-MANAGER GROUP  ═════════════════════╗
║ DM-Router  (o3-mini)   → classify: file | kb_search | request   ║
║ DM-Critic  (4.1-mini)  → OK / ask-again                        ║
║ Slots ↔ Redis, follow-up loop while intent=="unknown"          ║
╚═══════════════════════════════╧═════════════════════════════════╝
                                      │
                                      ▼
╔═══════════════════  KB-SEARCH AGENT  ═══════════════════╗
║ 1) Qdrant `dialogs`  → reuse if sim≥0.95                ║
║ 2) Qdrant `docs`     → rag_hits + similar_dialogs       ║
║ status: searching / web-search                          ║
╚═════════════════════════════════════════════════════════╝
                                      │ (context)
                                      ▼
╔════════════════ Planner (gpt-4.1) ═════════════════╗
║ build_plan(), need_clarify?, need_escalate?        ║
║ draft+Critic → UI  |  plan[] + context → Expert-GC ║
╚════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔══════════════  EXPERT GROUP CHAT (AutoGen)  ══════════════╗
║ • **DomainExpert** (gpt-4.1)   – Infowatch-Expert / …    ║
║ • Search-Tool (o3-mini)        – local + web_search      ║
║ • Critic-Expert (4.1-mini)     – OK / ADD_SEARCH         ║
║ • **EvidenceAggregator** (4.1-mini) – финальная проверка ║
║ status: step i/N, generating;  timeout 5 min             ║
╚══════════════════════════════════════════════════════════╝
                                      │
                         Refine-Paraphraser (o3-mini)
                                      │
                                      ▼
                                UI  (React)
                                   • Message bubbles (MD)
                                   • Live status & progress
                                   • Copy-button, citation pop-up
──────────────────────────────────────────────────────────────────────────────
                     ───── DATA & INFRA LAYER ─────
 Redis – slots, rate-limit, status_bus, web_search cache (TTL 24h)  
 SQLite – `dialog_log` (FULL chat ≤90 д); TTL-cron → MinIO archive  
 Qdrant – `docs` (RAG) • `dialogs` (re-use)        (dynamic-k)  
 MinIO  – PDF / чек-листы (File-Search)  
 Prometheus + Alertmanager – ib_* metrics, latency & timeout alerts  
 Grafana/Loki/Jaeger – dashboards, traces (“step i/N”, local_search)  
 k6 load-test (nightly CI)

──────────────────────────────────────────────────────────────────────────────
                     ───── МОДЕЛИ ─────
o3-mini   → DM-Router, embeddings, Search-Tool, Refiner, browser_search  
4.1-mini → DM-Critic, Critic-Expert, EvidenceAggregator  
gpt-4.1  → Planner, DomainExpert(s)

──────────────────────────────────────────────────────────────────────────────
                     ───── ПОТОК ЗАПРОСА ─────
User ► DM-Router/DM-Critic ► KB-Search (reuse?) ► Planner  
    └ file-shortcut → File-Search → URL  
             └ need_escalate → Expert-GC (multi-round) → Refine ► UI

*Все стадии публикуют status-event; таймауты (web 20 s / GC 300 s) отсекают долгие операции, отправляя системное ⚠️-сообщение.*

### Мониторинг и дашборды

Система включает в себя полноценный стек мониторинга на базе Prometheus и Grafana.

- **Prometheus**: Собирает метрики с бэкенда (`/metrics`), включая счетчики запросов (`ib_req_total`), задержки (`ib_stage_latency_sec`), таймауты (`ib_timeout_total`) и другие. Также настроены правила для алертов (`alert.rules.yml`).
- **Grafana**: Предоставляет готовый дашборд "IB-Assistant Overview" для визуализации ключевых метрик.

**Как получить доступ к дашборду:**
1. Запустите все сервисы: `docker-compose up -d`.
2. Откройте Grafana в браузере: [http://localhost:3000](http://localhost:3000).
3. Войдите с учетными данными по умолчанию: `admin` / `admin`.
4. Перейдите в раздел `Dashboards`. Дашборд "IB-Assistant Overview" должен быть уже доступен, так как он автоматически импортируется при старте контейнера Grafana.

### Память

Система использует несколько уровней памяти для эффективной работы:

1.  **Краткосрочная память (слоты)**:
    *   **Технология**: Redis.
    *   **Назначение**: Хранение ключевых сущностей (таких как `product`, `task`, `file_key`) в рамках одной сессии. Это позволяет агентам быстро получать доступ к контексту текущего диалога.

2.  **Долгосрочная память (логи диалогов)**:
    *   **Технология**: SQLite, таблица `dialog_log`.
    *   **Назначение**: После каждого ответа ассистента полная ветка диалога (вопрос-ответ) сохраняется в базу данных в формате JSON. Это обеспечивает полную историю переписки для анализа и отладки.

3.  **База знаний (векторы)**:
    *   **Технология**: Qdrant, коллекции `docs` и `dialogs`.
    *   **Назначение**:
        *   **`docs`**: Хранит векторы из проиндексированных документов (PDF, DOCX и т.д.).
        *   **`dialogs`**: После завершения диалога пара (вопрос пользователя, финальный ответ ассистента) векторизуется и добавляется в эту коллекцию.
    *   **Процесс поиска**: `KB-Search-Agent` выполняет двухэтапный поиск с умным переиспользованием:
        *   **Этап 1**: Поиск в `dialogs` с проверкой similarity score (≥0.95 = reuse, 0.60-0.95 = контекст).
        *   **Этап 2**: Поиск в `docs` для получения RAG-контекста.
        *   **Результат**: Либо готовый ответ из памяти, либо обогащенный контекст для Planner'а.

### Новая упрощенная архитектура

**Dialog Manager** заменил сложный Router и теперь обрабатывает входящие сообщения по простой логике:

1. **Классификация small_talk / file / request** выполняется моделью **o3-mini** по короткому промпту, без статических словарей.
2. **DM-Critic (4.1-mini)** повторно проверяет решение (score ≥ 0.5).
3. **File shortcuts** — если в slots есть `file_key`, сразу возвращает ссылку на файл
4. **Все остальное** — передается **Planner**-агенту для анализа

**Planner** принимает решение и возвращает структурированный ответ:
- `need_clarify: true` → запрос уточнения у пользователя
- `need_escalate: true` → передача сложного вопроса экспертной группе (ExpertGC)
- `draft` → готовый ответ от планировщика

### Диалог-менеджер

1. Извлекает текущие slots (product/task/…).
2. o3-mini классифицирует intent → {file | kb_search | request | small_talk} + confidence.
3. DM-Critic (4.1-mini) подтверждает. Если <0.5 → intent=unknown.
4. unknown / small_talk → follow-up или courtesy.
5. file → File-Search; **kb_search/request** → **KB-Search-Agent** → Planner.

### KB-Search-Agent

**Новый агент** для интеллектуального поиска по базе знаний и переиспользования готовых ответов:

1. **Проверяет коллекцию `dialogs`**:
   - **≥0.95** → ответ из памяти (reuse).
   - **0.60–0.95** → добавляет `similar_dialogs` в context.
   - **<0.60** → игнорирует как нерелевантные.

2. **Забирает фрагменты `docs` (RAG)**:
   - Поиск по документации с динамическим `k`.
   - Добавляет результаты в `context.rag`.

3. **Возвращает (status, context) Dialog-Manager'у**:
   - `("reuse", answer)` → готовый ответ пользователю.
   - `("escalate", context)` → передача Planner'у с обогащенным контекстом.

**Динамический k**: `k = max(3, min(10, expected_tokens // 400))` — адаптивное количество результатов поиска в зависимости от ожидаемой длины ответа.

### Expert-GC: Доменные эксперты и Агрегатор

**Экспертная группа** получает план от Planner'а и структурированно его выполняет. Архитектура была обновлена для повышения качества и надежности ответов.

- **Динамический выбор эксперта**: На основе слота `product` из диалога, система выбирает одного из двух экспертов:
    - **`Product_Expert`**: Специализированный агент, который "заточен" на конкретный продукт (например, "IB-v2_Expert"). Его системный промпт содержит указание фокусироваться на этом продукте.
    - **`General_Expert`**: Агент для общих вопросов, если продукт не указан.
- **Состав группы**:
    1. **Доменный эксперт** (Product или General) - ведущий агент.
    2. **Search** - агент с инструментом `local_search` для поиска по базе знаний.
    3. **Critic** - агент, оценивающий релевантность и полноту найденной информации.
    4. **EvidenceAggregator** - финальный агент, который собирает все доказательства, синтезирует из них единый, структурированный ответ и обязательно добавляет блок с цитатами.
- **Порядок работы**:
    1. Эксперт инициирует обсуждение.
    2. Search и Critic предоставляют и оценивают информацию.
    3. Aggregator имеет последнее слово, чтобы гарантировать, что ответ основан на фактах и содержит ссылки на источники.
- **Инструменты**: `local_search` для поиска по документации с автоматическими цитатами.

### Инструмент `web_search`
* Асинхронный вызов OpenAI Browser-tool.
* Таймаут задаётся `WEB_SEARCH_TIMEOUT_SEC` (по умолчанию 20 с).
* При срабатывании таймаута Search-агент возвращает строку **TIMEOUT**,
  Critic снижает уверенность → Expert-GC переходит к fallback-циклу.

### UX Flow

Первое приветствие («Здравствуйте! ...») генерируется на фронте
при загрузке страницы. Если пользователь действительно пишет
«Привет» — бэкенд отвечает коротким приветствием второй раз.

## Frontend Dev

```bash
cd frontend
npm i         # первый раз
npm run dev   # http://localhost:5173
```

Фронтенд использует:
- React + TypeScript
- Tailwind CSS для стилизации
- WebSocket для real-time общения с бэкендом
- Роли сообщений: `user`, `assistant`, `assistant(f/u)` для follow-up ответов

### Таймауты
| Env                | default | Что ограничивает |
|--------------------|---------|------------------|
| GC_TIMEOUT_SEC     | 300     | Expert-GC (AutoGen) |
| WEB_SEARCH_TIMEOUT_SEC | 20  | web-browser search-tool |

При превышении таймаута пользователь получает системное
сообщение «⚠️ Время вышло…».  Значения можно изменить
переменными среды (docker-compose, Helm values).

## Отладка Planner

Если планировщик возвращает некорректный JSON, система автоматически логирует сырые ответы модели для анализа:

```bash
# Подключаться к базе данных SQLite
sqlite3 /data/chatlog.db

# Просмотр последних сырых ответов модели
select content from chatlog where role='raw' order by id desc limit 5;

# Поиск ошибок JSON по времени
select ts, content from chatlog where role='raw' and ts > datetime('now', '-1 hour');

# Анализ всех сырых ответов для конкретного потока
select turn_index, content from chatlog where thread_id='your-thread-id' and role='raw';
```

**Возможные проблемы:**
- Модель возвращает JSON с комментариями или дополнительным текстом
- Неэкранированные кавычки в строковых полях
- Лишние запятые в конце объектов
- Ответ не в формате JSON

**Решение:** Система автоматически пытается извлечь JSON из текста, но если это невозможно, пользователь получит сообщение "🤖 Пока не понял формулировку, уточните пожалуйста."
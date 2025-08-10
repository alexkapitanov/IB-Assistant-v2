### Архивирование диалогов

## Development helpers

Install pre-commit to run ruff/black (Python) and eslint/prettier (frontend) on commit:

1. pip install pre-commit
2. pre-commit install

Or use Makefile helpers:

- make lint — static checks
- make fix — autofix formatting/lints
- make typecheck — mypy/tsc
- make test — pytest
- make sweep — clean caches and build artifacts

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

## Web-Search Cache

Веб-поиск кешируется в Redis на основе канонизированного ключа `canonicalize(query, slots)`:
- Нормализация: обрезка/склейка пробелов, lowercase
- Учет слотов: `topic` и `product` добавляются как суффиксы к ключу
- Итоговый ключ: `ws:<sha1(canonical)>`

Поведение:
- Успешные результаты сохраняются на `WEB_CACHE_TTL_SEC` (по умолчанию 24 часа)
- Негативный кеш (пустой ответ/таймаут) сохраняется строкой `"TIMEOUT"` на `WEB_CACHE_NEG_TTL_SEC` (по умолчанию 60 сек)
- Защита от шторма: перед реальным поиском берётся `NX`-lock на `WEB_CACHE_LOCK_SEC` (по умолчанию 30 сек);
    если лок не получен — ожидаем до 5 секунд заполнения кеша и читаем уже готовые данные
- Метрики Prometheus:
    - `ib_web_cache_hit_total`, `ib_web_cache_miss_total`, `ib_web_cache_hit_after_wait_total`
    - `ib_web_cache_store_total`, `ib_web_cache_store_negative_total`
    - `ib_web_search_latency_sec` (Histogram)

Формат результата `web_search()`:
- При успехе: `{ "summary": "...", "sources": [...], "ts": <unix_time> }`
- При таймауте или пустом результате: строка `"TIMEOUT"`

Сжатие:
- Если сериализованный payload > 100 КБ, сохраняется в gzip + base64 с префиксом `z:`.

Invalidate:
- Временно вручную: `redis-cli DEL ws:<sha1>`
- Планируется утилита: `scripts/ws_cache_invalidate.py` (в будущих задачах).

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

## Сервисы и порты

Активные сервисы в docker-compose:

- backend — FastAPI/gRPC сервер (экспортирует Prometheus /metrics)
- frontend — готовая статика UI на Nginx
- redis — кэш/слоты/шина статусов
- qdrant — векторное хранилище (RAG)
- minio — S3-совместимое хранилище (+ консоль)
- grafana — дашборды
- prometheus — сбор метрик
 - fake-openai — тестовый сервис для детерминированных ответов (профиль docker compose: test)

Порты (host → container):

- Backend API: 8000 → 8000
- Backend metrics: 9310 → 9310
- gRPC: 50051 → 50051
- Frontend: 5173 → 80
- Qdrant: 6333 → 6333
- MinIO S3: 9000 → 9000
- MinIO Console: 9001 → 9001
- Grafana: 3000 → 3000
- Prometheus: 9090 → 9090

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
║ Slots ↔ Redis: products extraction, criteria memory            ║
║ CLARIFY_THRESHOLD=0.6 + slot-memory для избежания повторов     ║
║ follow-up loop while intent=="unknown"                         ║
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

## Структура промптов

Все системные промпты собраны в одном модуле: `backend/prompts/system_messages.py`.

- SYSTEM_DOMAIN_EXPERT — системный промпт доменного эксперта (под тему/продукт)
- SYSTEM_GENERAL_EXPERT — общий эксперт по ИБ
- SYSTEM_AGGREGATOR — агрегатор доказательств и финального ответа

Использование в коде:

```python
from backend.prompts.system_messages import (
    SYSTEM_DOMAIN_EXPERT,
    SYSTEM_GENERAL_EXPERT,
    SYSTEM_AGGREGATOR,
)
```

Черновики/дубликаты удалены; единый файл упрощает поддержку и поиск по коду.

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

### Доменные эксперты

**Экспертная группа** получает план от Planner'а и структурированно его выполняет. Архитектура обновлена для адаптивного создания экспертов и качественной агрегации ответов.

* **DomainExpert** — создаётся динамически на основе slots.topic / product:
    - Использует слот `topic` (DLP, SIEM, Zero Trust, Linux hardening, SOC) для специализации
    - Если указан `product` (InfoWatch, McAfee, и др.), добавляется фокус на конкретный продукт
    - Имя эксперта формируется как `{product or topic}-Expert`
    - Системный промпт адаптируется под тематику: "Вы технический эксперт по теме «{topic}»{product_clause}"

* **EvidenceAggregator** проверяет ссылки и формирует итоговый блок «### Ссылки»:
    - Убеждается, что каждый абзац содержит ссылку вида [n]
    - Добавляет раздел «### Ссылки» с URL-адресами и описаниями
    - Возвращает финальный ответ с префиксом «FINAL_ANSWER:»

* **Статусы step i/N публикуются в статус-шину, UI показывает прогресс**:
    - Каждый шаг плана транслируется как "step {i}/{total}"
    - Пользователь видит прогресс выполнения в режиме реального времени
    - Завершение отмечается статусом "done"

**Состав группы**: DomainExpert + Search + Critic + Aggregator (AutoGen GroupChat, max_round=8)

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

## Недавние обновления

### Slot-Memory система
* **DM-Router** теперь использует Redis slot-memory для запоминания ключевой информации о диалоге
* Автоматическое извлечение продуктов ИБ: Symantec, McAfee, Forcepoint, Trend Micro, InfoWatch
* Сохранение критериев выбора при упоминании слова "критер" в сообщении пользователя
* Настраиваемый порог уточнений: `CLARIFY_THRESHOLD=0.6` (по умолчанию)
* **Planner** получает расширенный контекст: резюме последних 4 сообщений + слоты
* Избежание повторных запросов на уточнение при наличии сохранённых критериев

**Решение:** Система автоматически пытается извлечь JSON из текста, но если это невозможно, пользователь получит сообщение "🤖 Пока не понял формулировку, уточните пожалуйста."
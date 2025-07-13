# Руководство по тестированию IB-Assistant-v2

## 📋 Обзор тестового покрытия

Проект имеет полноценное тестовое покрытие с **76+ тестами** в **8 тестовых модулях**:

### 🧪 Тестовые модули

| Модуль | Назначение | Тесты |
|--------|------------|-------|
| `conftest.py` | Общие фикстуры и конфигурация | Фикстуры |
| `test_backend.py` | Backend компоненты (embeddings, memory) | 7 тестов |
| `test_api.py` | FastAPI endpoints и обработка ошибок | 14 тестов |
| `test_agents.py` | Агенты поиска и обработки | 12 тестов |
| `test_scripts.py` | Скрипты индексации и CLI | 15 тестов |
| `test_integration.py` | Интеграционные тесты системы | 12 тестов |
| `test_performance.py` | Тесты производительности | 8 тестов |
| `test_*_existing.py` | Существующие тесты | 8 тестов |

## 🏷️ Маркеры тестов

Тесты организованы с помощью pytest маркеров:

```bash
# Быстрые unit тесты (без внешних зависимостей)
pytest -m "not slow and not integration and not openai"

# Тесты с OpenAI API
pytest -m openai

# Интеграционные тесты (требуют Docker сервисы)
pytest -m integration

# Медленные/производительные тесты
pytest -m slow
```

## 🚀 Запуск тестов

### Базовые команды

```bash
# Все доступные тесты
pytest tests/

# Только быстрые unit тесты
pytest tests/ -m "not slow and not integration and not openai"

# С подробным выводом
pytest tests/ -v

# Конкретный модуль
pytest tests/test_backend.py

# Конкретный тест
pytest tests/test_backend.py::TestEmbedding::test_embedding_mock_response
```

### Продвинутые команды

```bash
# Только failed тесты
pytest tests/ --lf

# Остановиться после первой ошибки
pytest tests/ -x

# Показать покрытие
pytest tests/ --cov=backend --cov=agents --cov=scripts

# Параллельный запуск
pytest tests/ -n auto
```

## 🐳 Тестирование с Docker

```bash
# Запуск сервисов для интеграционных тестов
docker-compose up -d

# Интеграционные тесты
pytest tests/ -m integration

# Тесты с реальным OpenAI API
OPENAI_API_KEY=your_key pytest tests/ -m openai
```

## 📊 Статистика покрытия

- **✅ 29 тестов проходят** (unit тесты без внешних зависимостей)
- **⏸️ 47 тестов пропускаются** (когда нет сервисов/API ключей)
- **🔧 Полное покрытие**: backend, agents, scripts, API, интеграция

## 🛠️ Автоматические проверки

### Фикстуры в conftest.py
- `client` - FastAPI тест клиент
- `mc` - MinIO клиент
- `qc` - Qdrant клиент
- `dummy_pdf/docx/txt` - тестовые файлы
- `unique_bucket/prefix` - уникальные имена для тестов

### Автоматические пропуски
- Тесты с OpenAI API пропускаются без `OPENAI_API_KEY`
- Интеграционные тесты пропускаются без Docker сервисов
- Graceful fallbacks для всех внешних зависимостей

## 🎯 Типы тестов

### Unit тесты
- Мокирование внешних сервисов
- Изолированное тестирование функций
- Быстрое выполнение (<10 секунд)

### Интеграционные тесты
- Тестирование полного пайплайна
- Реальные сервисы (MinIO, Qdrant, Redis)
- Проверка взаимодействия компонентов

### Тесты производительности
- Время выполнения операций
- Использование памяти
- Concurrent testing
- Stress testing

### E2E тесты
- CLI интерфейсы
- API endpoints
- Полные пользовательские сценарии

## 🚨 CI/CD

GitHub Actions автоматически запускает:
```yaml
- Unit тесты (всегда)
- Docker build тесты
- Интеграционные тесты (если сервисы доступны)
- Автоматические пропуски без OpenAI API
```

## 📝 Добавление новых тестов

1. **Выберите подходящий модуль** или создайте новый
2. **Используйте маркеры** для категоризации
3. **Добавьте моки** для внешних сервисов
4. **Проверьте автоматические пропуски**

Пример:
```python
@pytest.mark.integration
@pytest.mark.openai
def test_new_feature(dummy_txt, mc, qc):
    # Ваш тест здесь
    pass
```

## 🔍 Debug тестов

```bash
# Подробный вывод ошибок
pytest tests/ --tb=long -v

# Вывод print statements
pytest tests/ -s

# Debug конкретного теста
pytest tests/test_backend.py::test_name --pdb
```

---

**Статус**: ✅ Полноценное покрытие готово
**Совместимость**: Python 3.11+, Docker, CI/CD
**Обновлено**: $(date)

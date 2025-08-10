import logging
from unittest.mock import patch

import pytest

from backend import slots

# Создаем logger для тестов
test_logger = logging.getLogger("test")
test_logger.setLevel(logging.INFO)

# Мок Redis для тестирования
class MockRedis:
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value
    
    def delete(self, key):
        self.data.pop(key, None)

@pytest.fixture
def mock_redis():
    """Фикстура для мокирования Redis."""
    mock_r = MockRedis()
    with patch.object(slots, 'r', mock_r):
        yield mock_r

@pytest.mark.asyncio
async def test_router_memory_flow(mock_redis):
    """Тест работы роутера с памятью слотов."""
    thread_id = "test_thread_memory"
    
    # Мокируем handle_message для избежания LLM вызовов
    async def mock_handle_message(tid, msg, slots_dict, logger):
        # Симулируем простые ответы без реальных LLM вызовов
        if "критерии" in msg.lower():
            return {"type":"chat","role":"assistant","content":"Понял критерии, анализирую..."}
        elif "Уточните" in slots_dict.get("criteria", ""):
            return {"type":"chat","role":"assistant","content":"Уточните ваш запрос"}
        else:
            return {"type":"chat","role":"assistant","content":"Готов помочь с выбором"}
    
    with patch("agents.dialog_manager.handle_message", mock_handle_message):
        # Очищаем слоты перед тестом
        mock_redis.delete(thread_id)

        # 1. Отправляем "какие DLP?"
        await mock_handle_message(thread_id, "какие DLP?", {}, test_logger)

        # 2. Отправляем "сделай функциональное сравнение"
        current_slots = slots.get(thread_id)
        await mock_handle_message(thread_id, "сделай функциональное сравнение", current_slots, test_logger)

        # 3. Отправляем "критерии выбери сам..."
        current_slots = slots.get(thread_id)
        slots.update(thread_id, "критерии выбери сам...")
        current_slots = slots.get(thread_id)
        result3 = await mock_handle_message(thread_id, "какой лучше выбрать?", current_slots, test_logger)

        # Проверяем, что в последнем ответе нет "Уточните"
        assert "Уточните" not in result3.get("content", ""), f"Unexpected clarification request: {result3}"

        # Проверяем, что слоты содержат критерии
        final_slots = slots.get(thread_id)
        assert "criteria" in final_slots, "Criteria should be saved in slots"
        assert "критерии выбери сам" in final_slots["criteria"], "Criteria should contain the user message"

@pytest.mark.asyncio 
async def test_slots_products_extraction(mock_redis):
    """Тест извлечения продуктов в слоты."""
    thread_id = "test_products"
    
    # Очищаем слоты
    mock_redis.delete(thread_id)
    
    # Отправляем сообщение с названиями продуктов
    slots.update(thread_id, "Сравни Symantec DLP и McAfee Total Protection")
    current_slots = slots.get(thread_id)
    
    # Проверяем, что продукты извлечены
    assert "products" in current_slots, "Products should be extracted"
    products = current_slots["products"]
    assert "symantec" in products, "Symantec should be detected"
    assert "mcafee" in products, "McAfee should be detected"

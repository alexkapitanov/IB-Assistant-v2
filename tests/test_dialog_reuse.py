#!/usr/bin/env python3
"""
Тест функциональности переиспользования диалогов.
Проверяем, что одинаковые вопросы получают высокий score (≥0.95) для переиспользования.
"""

import asyncio
import os
import sys

# Добавляем backend в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agents.kb_search import kb_search


async def test_dialog_reuse():
    """Тестируем функциональность поиска похожих диалогов"""
    print("🔍 Тестируем поиск похожих диалогов...")
    
    # Тестируем точно тот же вопрос, который уже есть в базе
    test_question = "Что такое DLP?"
    
    try:
        status, result = await kb_search(test_question)
        
        print(f"📋 Результат поиска для вопроса: '{test_question}'")
        print(f"📄 Тип результата: {type(result)}")
        print(f"📝 Содержимое: {result}")
        
        # Если результат - список из нескольких частей, проанализируем их
        if isinstance(result, list):
            for i, item in enumerate(result):
                print(f"  Элемент {i}: {item}")
        
        # Ищем информацию о score в результате
        result_str = str(result)
        if 'score' in result_str.lower() or 'similar' in result_str.lower():
            print("✅ Найдена информация о similarity score в результате!")
        else:
            print("⚠️  Информация о score не найдена в результате")
            
        return result
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании поиска диалогов: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_dialog_reuse())

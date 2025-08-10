#!/usr/bin/env python3
"""
Тестирование ассистента: простые вопросы → Dialog Manager + Critic, сложные → Expert Team
"""
import asyncio
import json

import websockets


async def test_assistant_question(question, description=""):
    """Отправляет вопрос ассистенту и возвращает ответ с деталями обработки."""
    print(f"\n{'='*60}")
    print(f"🧪 ТЕСТ: {description}")
    print(f"❓ Вопрос: {question}")
    print("-" * 60)
    
    try:
        # Подключаемся к WebSocket
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            
            # Отправляем сообщение
            message = {"message": question}
            await websocket.send(json.dumps(message))
            print(f"📤 Отправлено: {question}")
            
            responses = []
            statuses = []
            
            # Собираем все ответы
            timeout_counter = 0
            while timeout_counter < 30:  # максимум 30 секунд ожидания
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "status":
                        status = data.get("status", "unknown")
                        statuses.append(status)
                        print(f"⏳ Статус: {status}")
                        
                    elif data.get("type") == "chat":
                        content = data.get("content", "")
                        responses.append(content)
                        print(f"💬 Ответ: {content[:100]}{'...' if len(content) > 100 else ''}")
                        break
                        
                    elif data.get("type") == "error":
                        error_content = data.get("content", "Unknown error")
                        print(f"❌ Ошибка: {error_content}")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_counter += 1
                    continue
            
            # Анализируем маршрутизацию
            route_analysis = analyze_routing(statuses)
            print(f"🔍 Маршрутизация: {route_analysis}")
            
            return {
                "question": question,
                "responses": responses,
                "statuses": statuses,
                "route": route_analysis
            }
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return {"error": str(e)}

def analyze_routing(statuses):
    """Анализирует статусы для определения маршрута обработки."""
    if not statuses:
        return "❓ Неизвестно"
    
    # Ищем индикаторы Expert Team
    expert_indicators = ["step", "generating", "web-search"]
    has_expert_team = any(any(indicator in status for indicator in expert_indicators) for status in statuses)
    
    # Ищем индикаторы простой обработки
    simple_indicators = ["thinking", "searching"]
    has_simple_flow = all(status in simple_indicators for status in statuses if status)
    
    if has_expert_team:
        return "🧠 Expert Team (сложный вопрос)"
    elif has_simple_flow:
        return "💭 Dialog Manager + Critic (простой вопрос)"
    else:
        return f"🔄 Смешанный маршрут: {statuses}"

async def run_assistant_tests():
    """Запускает серию тестов для проверки маршрутизации."""
    
    print("🚀 Тестирование маршрутизации ассистента")
    print("=" * 60)
    
    # Тест 1: Простой вопрос (должен идти через Dialog Manager)
    test1 = await test_assistant_question(
        "Что такое SIEM?",
        "Простой вопрос (определение)"
    )
    
    # Тест 2: Вопрос средней сложности  
    test2 = await test_assistant_question(
        "Какие есть производители антивирусов?",
        "Средний вопрос (список)"
    )
    
    # Тест 3: Сложный аналитический вопрос (должен идти к Expert Team)
    test3 = await test_assistant_question(
        "Проведи детальное сравнение Symantec DLP и McAfee Total Protection по критериям безопасности, производительности и стоимости с рекомендациями для крупного предприятия",
        "Сложный аналитический вопрос"
    )
    
    # Тест 4: Вопрос с использованием слотов
    test4 = await test_assistant_question(
        "Сравни Trend Micro и InfoWatch критерии выбора определи сам",
        "Вопрос с продуктами и критериями (слоты)"
    )
    
    # Резюме тестирования
    print(f"\n{'='*60}")
    print("📊 РЕЗЮМЕ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    tests = [
        ("Простой вопрос", test1),
        ("Средний вопрос", test2), 
        ("Сложный вопрос", test3),
        ("Вопрос со слотами", test4)
    ]
    
    for test_name, result in tests:
        if "error" in result:
            print(f"❌ {test_name}: Ошибка - {result['error']}")
        else:
            route = result.get("route", "Неизвестно")
            print(f"✅ {test_name}: {route}")
    
    print("\n🎯 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:")
    print("- Простые вопросы → Dialog Manager + Critic")
    print("- Сложные аналитические → Expert Team")
    print("- Вопросы со слотами → сохранение контекста")
    print("- Статусы: thinking → searching → [step 1/N] → generating")

if __name__ == "__main__":
    asyncio.run(run_assistant_tests())

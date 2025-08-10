#!/usr/bin/env python3
"""
Тестирование Dialog Manager и Critic с разными типами сообщений
"""
import asyncio
import logging
import sys

from dotenv import load_dotenv  # noqa: E402

# Загружаем переменные окружения из .env файла
load_dotenv()

# Добавляем путь к backend для импорта модулей
sys.path.append('/workspaces/IB-Assistant-v2/backend')  # noqa: E402

from backend.agents.critic import ask_critic  # noqa: E402
from backend.agents.dialog_manager import handle_message  # noqa: E402

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_dialog_manager_and_critic():
    """Тестирует Dialog Manager и Critic с тремя разными сообщениями"""
    
    print("🧪 ТЕСТИРОВАНИЕ DIALOG MANAGER И CRITIC")
    print("=" * 60)
    
    # Тестовые данные
    test_cases = [
        {
            "message": "Привет!",
            "description": "Small talk (приветствие)",
            "slots": {},
            "expected_intent": "small_talk"
        },
        {
            "message": "Что такое SIEM?",
            "description": "Простой вопрос (определение)",
            "slots": {},
            "expected_intent": "request"
        },
        {
            "message": "Сравни антивирусы Kaspersky и Dr.Web по критериям безопасности",
            "description": "Сложный аналитический вопрос",
            "slots": {"products": ["kaspersky", "dr.web"], "criteria": "безопасность"},
            "expected_intent": "request"
        }
    ]
    
    # Создаем logger для тестов
    logger = logging.getLogger("test_dialog_manager")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"📝 ТЕСТ {i}: {test_case['description']}")
        print(f"❓ Сообщение: '{test_case['message']}'")
        print(f"🎰 Слоты: {test_case['slots']}")
        print("-" * 60)
        
        # Тестируем Dialog Manager
        try:
            thread_id = f"test_thread_{i}"
            response = await handle_message(
                thread_id=thread_id,
                user_q=test_case['message'],
                slots=test_case['slots'],
                session_logger=logger
            )
            
            print("✅ Dialog Manager ответ:")
            print(f"   Тип: {response.get('type', 'unknown')}")
            print(f"   Роль: {response.get('role', 'unknown')}")
            print(f"   Контент: {response.get('content', '')[:100]}{'...' if len(response.get('content', '')) > 100 else ''}")
            
            # Если это простой ответ (draft), тестируем Critic
            if response.get('type') == 'chat' and 'need_escalate' not in str(response):
                print("\n🔍 Тестируем Critic для ответа...")
                content = response.get('content', '')
                if content and len(content.strip()) > 10:  # Только если есть содержательный ответ
                    try:
                        critic_result = await ask_critic(content)
                        print(f"   Critic оценка: {'✅ ОДОБРЕНО' if critic_result else '❌ ОТКЛОНЕНО'}")
                        print(f"   Результат: {critic_result}")
                    except Exception as e:
                        print(f"   ❌ Ошибка Critic: {e}")
                else:
                    print("   ⚠️ Недостаточно контента для Critic")
            else:
                print("   ℹ️ Ответ эскалирован к Expert Team, Critic не применяется")
                
        except Exception as e:
            print(f"❌ Ошибка Dialog Manager: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("📊 ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ CRITIC")
    print("=" * 60)
    
    # Дополнительные тесты только для Critic
    critic_test_texts = [
        {
            "text": "SIEM - это система мониторинга безопасности.",
            "description": "Краткий ответ"
        },
        {
            "text": "SIEM (Security Information and Event Management) — это комплексная система для сбора, анализа и корреляции событий информационной безопасности. Она включает в себя функции централизованного логирования, real-time мониторинга, обнаружения аномалий и автоматического реагирования на инциденты. SIEM позволяет организациям получить единое представление о состоянии ИБ.",
            "description": "Подробный ответ"
        },
        {
            "text": "Да, есть антивирусы.",
            "description": "Слишком краткий ответ"
        }
    ]
    
    for i, test in enumerate(critic_test_texts, 1):
        print(f"\n🔍 CRITIC ТЕСТ {i}: {test['description']}")
        print(f"📝 Текст: {test['text'][:80]}{'...' if len(test['text']) > 80 else ''}")
        
        try:
            result = await ask_critic(test['text'])
            status = "✅ ОДОБРЕНО" if result else "❌ ОТКЛОНЕНО"
            print(f"   Результат: {status} ({result})")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n🎯 РЕЗЮМЕ:")
    print("- Dialog Manager обрабатывает разные типы сообщений")
    print("- Critic оценивает качество ответов по полноте")
    print("- Простые вопросы → draft + Critic")
    print("- Сложные вопросы → эскалация к Expert Team")

if __name__ == "__main__":
    asyncio.run(test_dialog_manager_and_critic())

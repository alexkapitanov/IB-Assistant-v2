#!/usr/bin/env python3
import re
import json

# Копируем логику из slots.py для тестирования
TOPIC_RE = re.compile(r"\b(DLP|SIEM|Zero\s+Trust|Linux\s+hardening|SOC)\b", re.I)

def test_topic_extraction():
    test_cases = [
        ("Расскажи про DLP системы", "DLP"),
        ("Нужна настройка SIEM решения", "SIEM"),
        ("Как внедрить Zero Trust архитектуру?", "Zero Trust"),
        ("Linux hardening best practices", "Linux hardening"),
        ("SOC процессы и процедуры", "SOC"),
        ("Обычный вопрос без тематики", None),
        ("DLP и SIEM интеграция", "DLP"),  # Должно найти первое совпадение
    ]
    
    print("🧪 Тестирование распознавания тематик:")
    print("=" * 50)
    
    for msg, expected in test_cases:
        match = TOPIC_RE.search(msg)
        found = match.group(0) if match else None
        
        status = "✅" if found == expected else "❌"
        print(f"{status} Сообщение: '{msg}'")
        print(f"   Ожидалось: {expected}")
        print(f"   Найдено: {found}")
        print()
    
    return True

def test_slots_logic():
    print("🧪 Тестирование полной логики slots:")
    print("=" * 50)
    
    # Мокаем функцию update
    def mock_update(msg):
        data = {}
        
        # products
        m = re.findall(r"(Symantec|McAfee|Forcepoint|Trend Micro|InfoWatch)", msg, re.I)
        if m: 
            data["products"] = list(set([p.lower() for p in m]))
        
        # topics
        if m := TOPIC_RE.search(msg):
            data["topic"] = m.group(0)
        
        # criteria
        if "критер" in msg.lower():
            data["criteria"] = msg.strip()
        
        return data
    
    test_messages = [
        "Расскажи про DLP системы InfoWatch",
        "Настройка SIEM McAfee в корпоративной сети",
        "Zero Trust архитектура без привязки к вендору",
        "Linux hardening серверов с Trend Micro",
        "SOC процессы и критерии их оценки"
    ]
    
    for msg in test_messages:
        result = mock_update(msg)
        print(f"📝 Сообщение: '{msg}'")
        print(f"🔍 Извлечено: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print()
    
    return True

if __name__ == "__main__":
    print("🚀 Запуск тестов slots.py")
    print("=" * 60)
    
    test_topic_extraction()
    test_slots_logic()
    
    print("✅ Все тесты завершены!")

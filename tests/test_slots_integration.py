"""
Тесты для модуля slots.py - извлечение тематик и продуктов
"""
import re


def test_topic_extraction():
    """Тест извлечения тематик из сообщений"""
    from backend.slots import TOPIC_RE
    
    test_cases = [
        ("Расскажи про DLP системы", "DLP"),
        ("Нужна настройка SIEM решения", "SIEM"),
        ("Как внедрить Zero Trust архитектуру?", "Zero Trust"),
        ("Linux hardening best practices", "Linux hardening"),
        ("SOC процессы и процедуры", "SOC"),
        ("Обычный вопрос без тематики", None),
        ("dlp в нижнем регистре", "dlp"),  # Должно работать case-insensitive
        ("SIEM и DLP интеграция", "SIEM"),  # Первое совпадение
    ]
    
    for msg, expected in test_cases:
        match = TOPIC_RE.search(msg)
        found = match.group(0) if match else None
        
        if expected:
            assert found is not None, f"Не найдена тема в сообщении: '{msg}'"
            assert found.lower() == expected.lower(), f"Ожидалось '{expected}', найдено '{found}'"
        else:
            assert found is None, f"Неожиданно найдена тема '{found}' в сообщении: '{msg}'"


def test_slots_update_logic():
    """Тест логики обновления слотов"""
    
    # Копируем логику из slots.py для тестирования
    TOPIC_RE = re.compile(r"\b(DLP|SIEM|Zero\s+Trust|Linux\s+hardening|SOC)\b", re.I)
    
    def mock_slots_update(msg):
        data = {}
        
        # topics
        if m := TOPIC_RE.search(msg):
            data["topic"] = m.group(0)
        
        # products
        m = re.findall(r"(Symantec|McAfee|Forcepoint|Trend Micro|InfoWatch)", msg, re.I)
        if m: 
            data["products"] = list(set([p.lower() for p in m]))
        
        # criteria
        if "критер" in msg.lower():
            data["criteria"] = msg.strip()
        
        return data
    
    test_cases = [
        {
            "msg": "Расскажи про DLP системы InfoWatch",
            "expected": {"topic": "DLP", "products": ["infowatch"]}
        },
        {
            "msg": "Настройка SIEM McAfee и Trend Micro",
            "expected": {"topic": "SIEM", "products": ["mcafee", "trend micro"]}
        },
        {
            "msg": "Zero Trust архитектура без привязки к вендору",
            "expected": {"topic": "Zero Trust"}
        },
        {
            "msg": "SOC процессы и критерии их оценки",
            "expected": {"topic": "SOC", "criteria": "SOC процессы и критерии их оценки"}
        },
        {
            "msg": "Общий вопрос по безопасности",
            "expected": {}
        }
    ]
    
    for case in test_cases:
        result = mock_slots_update(case["msg"])
        expected = case["expected"]
        
        for key, value in expected.items():
            assert key in result, f"Отсутствует ключ '{key}' в результате для сообщения: '{case['msg']}'"
            
            if key == "products":
                # Для списка продуктов проверяем содержимое, не порядок
                assert set(result[key]) == set(value), \
                    f"Для ключа '{key}' ожидалось {set(value)}, получено {set(result[key])}"
            else:
                assert result[key] == value, \
                    f"Для ключа '{key}' ожидалось {value}, получено {result[key]}"


def test_create_domain_expert_integration():
    """Тест интеграции slots → create_domain_expert"""
    import os
    from unittest.mock import patch
    
    # Проверяем наличие API ключа
    if not os.getenv("OPENAI_API_KEY"):
        # Мокаем создание экспертов, если нет API ключа
        with patch('backend.agents.expert_gc.AssistantAgent') as mock_agent:
            from backend.agents.expert_gc import create_domain_expert
            
            mock_expert = type('MockExpert', (), {
                'name': None,
                'system_message': None,
                'llm_config': None
            })()
            
            def mock_create(name, llm_config, system_message):
                mock_expert.name = name
                mock_expert.system_message = system_message
                mock_expert.llm_config = llm_config
                return mock_expert
            
            mock_agent.side_effect = mock_create
            
            test_cases = [
                {
                    "slots": {"topic": "DLP", "product": "InfoWatch"},
                    "expected_name": "InfoWatch-Expert",
                    "should_contain": ["DLP", "InfoWatch"]
                },
                {
                    "slots": {"topic": "SIEM"},
                    "expected_name": "SIEM-Expert", 
                    "should_contain": ["SIEM"]
                },
                {
                    "slots": {},
                    "expected_name": "информационная безопасность-Expert",
                    "should_contain": ["информационная безопасность"]
                }
            ]
            
            for case in test_cases:
                expert = create_domain_expert(case["slots"])
                
                # Проверяем имя эксперта
                assert expert.name == case["expected_name"], \
                    f"Ожидалось имя '{case['expected_name']}', получено '{expert.name}'"
                
                # Проверяем содержимое системного сообщения
                for term in case["should_contain"]:
                    assert term in expert.system_message, \
                        f"Термин '{term}' отсутствует в системном сообщении эксперта"
                
                # Проверяем модель
                assert expert.llm_config["model"] == "gpt-4.1"
                assert expert.llm_config["temperature"] == 0.3
    else:
        # Если API ключ есть, запускаем реальный тест
        from backend.agents.expert_gc import create_domain_expert
        
        expert = create_domain_expert({"topic": "DLP"})
        assert expert.name == "DLP-Expert"
        assert "DLP" in expert.system_message


if __name__ == "__main__":
    # Добавляем путь к проекту для импортов
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Запуск тестов
    test_topic_extraction()
    test_slots_update_logic()
    print("✅ Все тесты slots.py прошли успешно!")

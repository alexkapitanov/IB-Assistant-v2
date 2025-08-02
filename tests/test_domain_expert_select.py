import pytest
from backend.agents.expert_gc import create_domain_expert, SYSTEM_EXPERT_TEMPLATE, SYSTEM_GENERAL_EXPERT
from backend import config

# Мокируем autogen, чтобы не требовать его установки для тестов
class MockAssistantAgent:
    def __init__(self, name, llm_config, system_message):
        self.name = name
        self.llm_config = llm_config
        self.system_message = system_message

@pytest.fixture(autouse=True)
def mock_autogen_for_tests(monkeypatch):
    """
    Автоматически мокирует autogen.AssistantAgent для всех тестов в этом файле.
    """
    monkeypatch.setattr("backend.agents.expert_gc.autogen.AssistantAgent", MockAssistantAgent)

def test_create_product_expert(monkeypatch):
    """
    Тест: Фабрика должна создавать эксперта по продукту, если слот 'product' предоставлен.
    """
    monkeypatch.setenv("MODEL_GPT4", "gpt-4-test-from-expert-test")
    slots = {"product": "IB-v2"}
    expert = create_domain_expert(slots)
    
    assert isinstance(expert, MockAssistantAgent)
    assert expert.name == "IB-v2_Expert"
    expected_message = SYSTEM_EXPERT_TEMPLATE.format(product="IB-v2")
    assert expert.system_message == expected_message
    assert expert.llm_config["model"] == config.MODEL_GPT4

def test_create_general_expert(monkeypatch):
    """
    Тест: Фабрика должна создавать эксперта по общим вопросам, если слот 'product' отсутствует.
    """
    monkeypatch.setenv("MODEL_GPT4", "gpt-4-test-from-general-test")
    slots = {"some_other_slot": "value"}
    expert = create_domain_expert(slots)
    
    assert isinstance(expert, MockAssistantAgent)
    assert expert.name == "General_Expert"
    assert expert.system_message == SYSTEM_GENERAL_EXPERT
    assert expert.llm_config["model"] == config.MODEL_GPT4

def test_create_general_expert_empty_slots(monkeypatch):
    """
    Тест: Фабрика должна создавать эксперта по общим вопросам при пустых слотах.
    """
    monkeypatch.setenv("MODEL_GPT4", "gpt-4-test-from-empty-slots-test")
    slots = {}
    expert = create_domain_expert(slots)
    
    assert isinstance(expert, MockAssistantAgent)
    assert expert.name == "General_Expert"
    assert expert.system_message == SYSTEM_GENERAL_EXPERT
    assert expert.llm_config["model"] == config.MODEL_GPT4

def test_product_name_with_spaces(monkeypatch):
    """
    Тест: Пробелы в названии продукта должны заменяться на подчеркивания в имени агента.
    """
    monkeypatch.setenv("MODEL_GPT4", "gpt-4-test-from-spaces-test")
    slots = {"product": "Super Cool Product"}
    expert = create_domain_expert(slots)
    
    assert expert.name == "Super_Cool_Product_Expert"
    expected_message = SYSTEM_EXPERT_TEMPLATE.format(product="Super Cool Product")
    assert expert.system_message == expected_message

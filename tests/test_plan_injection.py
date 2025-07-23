import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from backend.agents.expert_gc import _inject_plan


def test_plan_injection():
    """Тест внедрения плана в Expert-GC"""
    
    # Создаем мок для GroupChatManager
    mock_mgr = Mock()
    mock_mgr.update_system_message = Mock()
    
    # Тестовый план
    test_plan = ["шаг1", "шаг2", "анализ данных"]
    
    # Вызываем функцию
    _inject_plan(mock_mgr, test_plan)
    
    # Проверяем, что update_system_message был вызван с правильным сообщением
    mock_mgr.update_system_message.assert_called_once()
    call_args = mock_mgr.update_system_message.call_args[0][0]
    
    # Проверяем содержимое сообщения
    assert "шаг1, шаг2, анализ данных" in call_args
    assert "Следуй по шагам плана:" in call_args
    assert "Отмечай выполненный пункт галочкой ✓" in call_args


def test_plan_injection_empty_plan():
    """Тест внедрения пустого плана"""
    
    mock_mgr = Mock()
    mock_mgr.update_system_message = Mock()
    
    # Пустой план
    empty_plan = []
    
    # Вызываем функцию
    _inject_plan(mock_mgr, empty_plan)
    
    # Проверяем, что функция все равно вызывается
    mock_mgr.update_system_message.assert_called_once()
    call_args = mock_mgr.update_system_message.call_args[0][0]
    
    # В сообщении должна быть пустая строка между ":" и "."
    assert "Следуй по шагам плана: ." in call_args


def test_plan_injection_single_step():
    """Тест внедрения плана с одним шагом"""
    
    mock_mgr = Mock()
    mock_mgr.update_system_message = Mock()
    
    # План с одним шагом
    single_step_plan = ["единственный шаг"]
    
    # Вызываем функцию
    _inject_plan(mock_mgr, single_step_plan)
    
    # Проверяем результат
    mock_mgr.update_system_message.assert_called_once()
    call_args = mock_mgr.update_system_message.call_args[0][0]
    
    assert "единственный шаг" in call_args
    assert "Следуй по шагам плана: единственный шаг." in call_args


@patch('backend.agents.expert_gc.autogen')
def test_run_expert_gc_with_plan_context(mock_autogen):
    """Интеграционный тест run_expert_gc с контекстом плана"""
    
    # Настраиваем моки для autogen
    mock_expert = Mock()
    mock_critic = Mock()
    mock_search = Mock()
    mock_gc = Mock()
    mock_mgr = Mock()
    
    # Мокаем результат чата как AsyncMock
    mock_chat_result = Mock()
    mock_chat_result.summary = "Тестовый ответ экспертной группы"
    mock_mgr.a_initiate_chat = AsyncMock(return_value=mock_chat_result)
    
    mock_autogen.AssistantAgent.side_effect = [mock_expert, mock_critic, mock_search]
    mock_autogen.GroupChat.return_value = mock_gc
    mock_autogen.GroupChatManager.return_value = mock_mgr
    
    # Импортируем функцию после настройки моков
    from backend.agents.expert_gc import run_expert_gc
    
    # Мокаем local_search
    with patch('backend.agents.expert_gc.local_search') as mock_local_search:
        mock_local_search.return_value = []
        
        # Тестовые данные
        thread_id = "test_thread"
        user_q = "Тестовый вопрос"
        slots = {}
        plan = {
            "context": {
                "plan": ["анализ угроз", "составление отчета", "рекомендации"]
            }
        }
        
        # Мокаем logger
        mock_logger = Mock()
        
        # Запускаем функцию
        import asyncio
        # Поскольку run_expert_gc - это async функция, ее нужно запускать в цикле событий
        with patch('backend.config.GC_TIMEOUT_SEC', 300): # Увеличиваем таймаут для теста
             result = asyncio.run(run_expert_gc(thread_id, user_q, slots, plan, mock_logger))
        
        # Проверяем, что update_system_message был вызван с планом
        # Мы не можем напрямую проверить _inject_plan, но можем убедиться,
        # что mgr был создан и чат инициирован
        mock_mgr.a_initiate_chat.assert_awaited_once()
        assert result["answer"] == "Тестовый ответ экспертной группы"
        assert result["model"] == "expert-group-chat"


@patch('backend.agents.expert_gc.autogen')
def test_run_expert_gc_without_plan_context(mock_autogen):
    """Тест run_expert_gc без контекста плана"""
    
    # Настраиваем моки
    mock_expert = Mock()
    mock_critic = Mock() 
    mock_search = Mock()
    mock_gc = Mock()
    mock_mgr = Mock()
    
    mock_chat_result = Mock()
    mock_chat_result.summary = "Ответ без плана"
    mock_mgr.a_initiate_chat = AsyncMock(return_value=mock_chat_result)
    
    mock_autogen.AssistantAgent.side_effect = [mock_expert, mock_critic, mock_search]
    mock_autogen.GroupChat.return_value = mock_gc
    mock_autogen.GroupChatManager.return_value = mock_mgr
    
    from backend.agents.expert_gc import run_expert_gc
    
    with patch('backend.agents.expert_gc.local_search') as mock_local_search:
        mock_local_search.return_value = []
        
        # План без context
        plan_without_context = {
            "need_escalate": True,
            "draft": ""
        }
        
        mock_logger = Mock()
        
        import asyncio
        with patch('backend.config.GC_TIMEOUT_SEC', 300): # Увеличиваем таймаут для теста
            result = asyncio.run(run_expert_gc("test", "вопрос", {}, plan_without_context, mock_logger))
        
        # Проверяем, что функция отработала без ошибок
        assert result["answer"] == "Ответ без плана"
        mock_mgr.a_initiate_chat.assert_awaited_once()

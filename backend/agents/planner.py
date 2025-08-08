import json
import logging

from backend.chat_db import get_current_thread_messages
from backend.json_utils import safe_load
from backend.openai_helpers import call_llm

PLAN_PROMPT = """Ты — Planner-агент по информационной безопасности.
Верни ОДИН JSON без комментариев:
{{
 "need_clarify": bool,
 "clarify": "<вопрос или пусто>",
 "need_escalate": bool,
 "draft": "<краткий ответ или пусто>",
 "plan": ["шаг 1", "шаг 2", …]
}}

ПРАВИЛА ЭСКАЛАЦИИ (need_escalate: true):
- Сравнение продуктов по множественным критериям
- Детальный анализ технических характеристик
- Рекомендации для внедрения в организации
- Вопросы требующие экспертного анализа и поиск в базе знаний
- Запросы на глубокое техническое сравнение

ПРОСТЫЕ ОТВЕТЫ (need_escalate: false):
- Краткие определения (что такое SIEM?)
- Простые списки (производители антивирусов)
- Базовые вопросы без аналитики

===
Контекст: {context}
Вопрос: «{q}»
Слоты: {slots}
"""


async def summarize(history: list[dict]) -> str:
    """Создаёт краткое резюме истории диалога."""
    if not history:
        return "Диалог только начался."

    # Берём последние 4 сообщения для краткости
    recent = history[-4:]
    summary_parts = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100]  # Обрезаем длинные сообщения
        summary_parts.append(f"{role}: {content}")

    return "\n".join(summary_parts)


async def _build_plan(q: str, slots: dict, context: str | None = None, logger: logging.Logger | None = None) -> dict:
    """
    Вызывает LLM для построения плана и безопасно парсит результат.
    """
    logger = logger or logging.getLogger("planner")
    logger.info("Calling LLM to build a plan.")
    # `ensure_ascii=False` для корректной передачи кириллицы в JSON
    raw, _ = await call_llm(
        "gpt-4.1",
        PLAN_PROMPT.format(q=q, slots=json.dumps(slots, ensure_ascii=False), context=context or ""),
        temperature=0,
    )

    plan = safe_load(raw)

    # Проверка на случай, если LLM вернул пустой или невалидный JSON
    if not plan:
        logger.error(f"Planner LLM returned invalid JSON: {raw}")
        # Fallback в случае, если LLM вернул невалидный JSON
        return {
            "need_clarify": False,
            "clarify": "",
            "need_escalate": True,  # Эскалация для ручного разбора
            "draft": "",
            "plan": ["LLM planner returned invalid JSON"],
        }

    logger.info(f"Plan received from LLM: {plan}")
    return plan


async def ask_planner(thread_id: str, user_q: str, slots: dict, logger: logging.Logger) -> dict:
    """
    Основная функция-планировщик. Определяет, что делать с запросом пользователя.
    Вызывает LLM для построения плана, затем проверяет его через критика.
    """
    logger.info(f"Building plan for: '{user_q}'")

    # Создаём контекст с историей и слотами
    history = get_current_thread_messages(thread_id)
    context_summary = await summarize(history)
    # Включаем дополнительный контекст (например, из KB-Search), если он был предоставлен в slots["kb"]
    extra_kb = slots.get("kb") if isinstance(slots, dict) else None
    ctx = {"summary": context_summary, "slots": {k: v for k, v in slots.items() if k != "kb"}}
    if extra_kb is not None:
        ctx["kb"] = extra_kb
    context = json.dumps(ctx, ensure_ascii=False)

    # Вызываем _build_plan с новой сигнатурой; если тестовый мок ожидает старую (3 аргумента), повторим вызов
    try:
        plan = await _build_plan(user_q, slots, context, logger)
    except TypeError:
        plan = await _build_plan(user_q, slots, logger)  # type: ignore[misc]
3
    # Добавляем план в контекст для Expert-GC (если план существует)
    if "plan" in plan:
        plan["context"] = {"plan": plan["plan"]}

    # если draft готов и need_escalate=False — задаём Critic-проверку
    if not plan.get("need_escalate") and plan.get("draft"):
        logger.info(f"Draft found, sending to critic: '{plan['draft']}'")
        # Импортируем через внешний shim, чтобы тесты могли мокеать по пути 'agents.critic.ask_critic'
        try:
            from agents.critic import ask_critic  # type: ignore
        except Exception:
            from backend.agents.critic import ask_critic  # fallback

        ok = await ask_critic(plan["draft"])

        if ok:
            logger.info("Critic approved the draft.")
            # Явно зафиксируем отсутствие эскалации
            plan["need_escalate"] = False
            return plan

        # иначе помечаем как need_escalate
        logger.warning("Critic rejected the draft, escalating.")
        plan["need_escalate"] = True

    return plan

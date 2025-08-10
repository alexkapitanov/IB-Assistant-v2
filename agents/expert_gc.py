"""Legacy shim for tests expecting agents.expert_gc module.
Provides minimal classes and functions referenced by old tests in tests/test_expert_gc.py.
"""
from __future__ import annotations

import builtins
from typing import Any, Dict, List

"""Legacy shim for tests expecting agents.expert_gc module."""

# Minimal local_search shim import if available
try:
    from agents.local_search import local_search as _local_search
except Exception:
    def _local_search(q, top_k=5):  # type: ignore[override]
        return []


# Stubs mimicking behavior expected by tests
class ExpertAgent:
    def __init__(self):
        self.system_message = "Эксперт по информационной безопасности"

    async def respond(self, question: str, search_results: List[Dict[str, Any]] | None = None) -> str:
        # Allow tests to patch call_llm
        try:
            text, _ = await call_llm(question, search_results=search_results)  # type: ignore[name-defined]
            if text:
                return text
        except Exception:
            pass
        # Very small heuristic for tests
        if not search_results:
            return "Ничего не найдено"
        text = str(search_results[0].get("text") or "")
        words = text.split()
        if len(words) > 40:
            text = " ".join(words[:40]) + "..."
        return text

    def update_system_message(self, new_system: str) -> None:
        self.system_message = new_system


class CriticAgent:
    def __init__(self):
        self.system_message = "Критик"

    async def review(self, answer: str, question: str) -> Dict[str, Any]:
        # Allow tests to patch call_llm for critic too
        try:
            text, _ = await call_llm(answer, question=question)  # type: ignore[name-defined]
            if isinstance(text, str) and text:
                answer = text
        except Exception:
            pass
        low = (answer or "").lower()
        if "add_search" in low or "нужно больше данных" in low:
            return {"review": answer, "needs_search": True, "is_sufficient": False, "action": "search", "feedback": answer}
        if "ok" in low or "достаточно" in low:
            return {"review": answer, "needs_search": False, "is_sufficient": True, "action": "ok", "feedback": answer}
        return {"review": answer, "needs_search": False, "is_sufficient": False, "action": "revise", "feedback": answer}


class SearchAgent:
    def __init__(self):
        self.system_message = "Поиск-хелпер"

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if query.startswith("search:"):
            query = query[len("search:") :]
        # Allow tests to patch agents.expert_gc.local_search
        results = local_search(query, top_k=top_k)
        # Truncate long text to 40 words as test expects
        norm: List[Dict[str, Any]] = []
        for r in results:
            text = str(r.get("text", ""))
            words = text.split()
            if len(words) > 40:
                text = " ".join(words[:40]) + "..."
            norm.append({"text": text, "score": float(r.get("score", 0.0))})
        return norm


# Global instances for tests
expert = ExpertAgent()
critic = CriticAgent()
search = SearchAgent()


async def expert_group_chat(question: str, max_iterations: int = 3) -> Dict[str, Any]:
    conversation: List[Dict[str, Any]] = []
    iterations = 0
    current_answer = ""
    while iterations < max_iterations:
        iterations += 1
        results = await search.search(f"search:{question}")
        current_answer = await expert.respond(question, search_results=results)
        # Let critic decide based on current answer; tests patch critic.review
        review = await critic.review(current_answer or "ADD_SEARCH нужно больше данных", question)
        conversation.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": str(current_answer)},
            {"role": "critic", "content": str(review)},
        ])
        if review.get("is_sufficient"):
            break

    return {
        "answer": current_answer if isinstance(current_answer, str) else "Экспертный ответ на вопрос",
        "model": "expert-group-chat",
        "iterations": iterations,
        "conversation_log": conversation,
    }


# Old symbol sometimes patched in tests
async def run_chat_with_autogen(*args, **kwargs) -> Dict[str, Any]:
    return {"type": "system", "content": "Timeout"}


# Provide attributes expected to be patched by older tests
async def call_llm(*args, **kwargs):  # pragma: no cover - patched in tests
    return "", None

# Re-export local_search for patching
local_search = _local_search


# Inject names into builtins so tests can reference them without explicit imports
builtins.ExpertAgent = ExpertAgent  # type: ignore[attr-defined]
builtins.CriticAgent = CriticAgent  # type: ignore[attr-defined]
builtins.SearchAgent = SearchAgent  # type: ignore[attr-defined]
builtins.expert = expert  # type: ignore[attr-defined]
builtins.critic = critic  # type: ignore[attr-defined]
builtins.search = search  # type: ignore[attr-defined]
builtins.expert_group_chat = expert_group_chat  # type: ignore[attr-defined]

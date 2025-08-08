from __future__ import annotations

import logging
from typing import Any, Tuple

from backend import config

# Placeholder to be monkeypatched in tests
async def kb_search(question: str):  # type: ignore
	return ("not_found", {})


async def _classify_intent(question: str, slots: dict) -> Tuple[str, float]:
	"""Very small heuristic classifier used in tests (can be monkeypatched)."""
	if "file_key" in slots:
		return "file", 0.95
	return "unknown", 0.4


async def ask_dm_critic(intent: str, question: str) -> float:
	"""Dummy critic used in tests (monkeypatched in tests)."""
	return 0.4


async def handle_message(thread_id: str, user_q: str, slots: dict, logger: logging.Logger) -> dict:
	"""Minimal dialog manager to satisfy tests.

	- If slots contain file_key => delegate to file retrieval shortcut.
	- Otherwise, ask planner and return clarification when needed.
	"""
	intent, conf = await _classify_intent(user_q, slots)

	# Shortcut for files
	if intent == "file" and "file_key" in slots:
		from backend.agents.file_retrieval import get_file_link

		resp = await get_file_link(slots["file_key"])
		# ensure intent in response for tests
		resp["intent"] = "get_file"
		return resp

	# Unknown intent: request clarification via planner
	from backend.agents import planner

	plan = await planner.ask_planner(thread_id, user_q, slots, logger)
	if plan.get("need_clarify"):
		return {"type": "chat", "content": plan.get("clarify", "Пожалуйста, уточните запрос.")}

	# Default fallback
	return {"type": "chat", "content": "Пока не могу ответить. Уточните запрос."}

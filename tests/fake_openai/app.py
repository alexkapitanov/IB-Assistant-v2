from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import time

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]

class ChatResponse(BaseModel):
    id: str
    model: str
    created: int
    choices: List[Dict[str, Any]]


def _detect_system(messages: List[Message]) -> str:
    for m in messages:
        if m.role == "system":
            return m.content or ""
    return ""


def _last_user(messages: List[Message]) -> str:
    for m in reversed(messages):
        if m.role == "user":
            return m.content or ""
    return ""


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def completions(req: ChatRequest):
    sys = _detect_system(req.messages)
    now = int(time.time())

    if "Aggregator" in sys:
        content = (
            "FINAL_ANSWER: Готовый ответ.\n\n### Ссылки\n¹ https://example.com\n² https://vendor.example/doc"
        )
    elif "Проверяй полноту" in sys or "Critic" in sys:
        content = "OK"
    elif "Ищи факты" in sys or "Search" in sys:
        content = '{"need_search": false}'
    elif "Вы технический эксперт" in sys or "DomainExpert" in sys:
        content = "Черновик по теме [¹]"
    elif "Планировщик" in sys or "Planner" in sys:
        content = '{"need_escalate": true, "plan": ["Шаг 1: собрать факты", "Шаг 2: сформировать ответ"]}'
    elif "DM-Router" in sys:
        q = _last_user(req.messages).lower()
        if any(w in q for w in ["опросник", "чек-лист", "скачай", "дай файл"]):
            content = '{"intent":"file","confidence":0.92}'
        else:
            content = '{"intent":"request","confidence":0.9}'
    else:
        content = "stubbed reply"

    return ChatResponse(
        id="cmpl-stub",
        model=req.model,
        created=now,
        choices=[{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    )

from pydantic import BaseModel
from typing import Literal, Any, List, Tuple, Optional

class WsOutgoing(BaseModel):
    type: Literal["status", "chat", "error"]
    role: str | None = None      # for type="chat"
    content: str | None = None
    citations: Optional[List[Tuple[int, str]]] = None  # Добавляем поддержку цитат
    status: Any | None = None  # Разрешаем любые строки для статуса
    payload: dict[str,Any] | None = None

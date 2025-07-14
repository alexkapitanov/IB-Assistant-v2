from pydantic import BaseModel
from typing import Literal, Any, List, Tuple, Optional

class WsOutgoing(BaseModel):
    type: Literal["status","chat"]
    role: str | None = None      # for type="chat"
    content: str | None = None
    citations: Optional[List[Tuple[int, str]]] = None  # Добавляем поддержку цитат
    status: Literal["thinking","searching","generating"] | None = None
    payload: dict[str,Any] | None = None

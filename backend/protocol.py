from pydantic import BaseModel
from typing import Literal, Any

class WsOutgoing(BaseModel):
    type: Literal["status","message"]
    role: str | None = None      # for type="message"
    content: str | None = None
    status: Literal["thinking","searching","generating"] | None = None
    payload: dict[str,Any] | None = None

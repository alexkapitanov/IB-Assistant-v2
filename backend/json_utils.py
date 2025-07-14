import json
import re


class BadJSON(RuntimeError):
    """Модель вернула строку, которую нельзя распарсить как JSON."""
    def __init__(self, message: str, raw_json: str = ""):
        super().__init__(message)
        self.raw_json = raw_json


def safe_load(text: str) -> dict:
    """
    Пытаемся json.loads(); если падает — вырезаем первое {...}
    и пытаемся ещё раз. При неудаче бросаем BadJSON.
    
    Args:
        text: Строка, которая должна содержать JSON
        
    Returns:
        dict: Распарсенный JSON объект
        
    Raises:
        BadJSON: Если не удалось распарсить JSON
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        raise BadJSON(f"{exc}. RAW: {text[:280]}…") from exc

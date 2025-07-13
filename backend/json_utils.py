import json
import re


class BadJSON(RuntimeError):
    """Исключение для некорректного JSON от LLM"""
    pass


def safe_load(txt: str):
    """
    Безопасный парсер JSON с попыткой извлечения из сырого текста
    
    Args:
        txt: Строка, которая должна содержать JSON
        
    Returns:
        dict: Распарсенный JSON объект
        
    Raises:
        BadJSON: Если не удалось распарсить JSON
    """
    try:
        return json.loads(txt)
    except json.JSONDecodeError as e:
        # Попытка вырезать JSON объект из текста
        m = re.search(r'\{.*\}', txt, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        
        # Если ничего не получилось
        raise BadJSON(f"Bad JSON: {e}\nRAW: {txt[:300]}")

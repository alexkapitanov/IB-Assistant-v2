from backend.openai_helpers import call_llm
import json, re

_PROMPT = """
Выдели product, vendor, task из фразы. Верни JSON, пустыe строки если нет.
Пример: {"product":"Infowatch DLP","task":"настройка"}
===
фраза: «{q}»
"""

_JSON_RE = re.compile(r'\{.*\}')

def extract_slots(q:str)->dict:
    raw,_ = call_llm("o3-mini", _PROMPT.format(q=q), temperature=0)
    m=_JSON_RE.search(raw)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}

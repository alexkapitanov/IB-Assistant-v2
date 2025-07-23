from backend.openai_helpers import call_llm
import re

def ask_dm_critic(intent:str, text:str)->float:
    prompt=f"Оцени правильность классификации '{intent}' для фразы:\n{text}\nТолько число 0-1."
    raw,_ = call_llm("4.1-mini", prompt, temperature=0)
    try: return float(re.search(r'(\d+(?:\.\d+)?)',raw).group(1))
    except: return 0.0

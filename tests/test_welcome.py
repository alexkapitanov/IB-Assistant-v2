import pathlib, re

def test_welcome_in_hook():
    hook_code = pathlib.Path("frontend/src/hooks/useChat.ts").read_text(encoding="utf-8")
    assert "Здравствуйте! Чем могу помочь по вопросам информационной безопасности?" in hook_code

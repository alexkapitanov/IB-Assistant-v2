import pathlib, re

def test_welcome_in_html():
    html = pathlib.Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    assert "Здравствуйте! Чем могу помочь" in html

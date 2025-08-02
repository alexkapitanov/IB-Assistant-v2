# Проверяем что VITE_GRAFANA_URL начинается с /
import os, json, pathlib
env = pathlib.Path("frontend/.env").read_text()
assert "VITE_GRAFANA_URL=/grafana" in env

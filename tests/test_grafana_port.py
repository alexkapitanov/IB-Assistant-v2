import yaml, pathlib, re

cfg = yaml.safe_load(pathlib.Path("docker-compose.yml").read_text())
assert "3000:3000" in cfg["services"]["grafana"]["ports"]

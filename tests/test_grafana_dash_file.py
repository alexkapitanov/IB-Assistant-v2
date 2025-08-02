import json
import pathlib


def test_dashboard_json():
    """
    Проверяет, что файл дашборда Grafana существует и содержит корректный заголовок.
    """
    dashboard_path = pathlib.Path("grafana/provisioning/dashboards_data/ib_assistant_overview.json")
    assert dashboard_path.exists(), f"Файл дашборда не найден по пути: {dashboard_path}"

    data = json.loads(dashboard_path.read_text())
    assert "title" in data, "В дашборде отсутствует поле 'title'"
    assert data["title"] == "IB Assistant Overview", "Некорректный заголовок дашборда"
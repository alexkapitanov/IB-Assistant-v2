import json

def test_dashboard_theme():
    dash = json.load(open('grafana/provisioning/dashboards_data/ib_assistant_overview.json'))
    # Проверяем, что дашборд имеет корректную структуру
    assert "title" in dash, "Дашборд должен иметь заголовок"
    assert "panels" in dash, "Дашборд должен иметь панели"
    assert len(dash["panels"]) > 0, "Дашборд должен содержать хотя бы одну панель"

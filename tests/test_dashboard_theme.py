import json

def test_dashboard_theme():
    dash = json.load(open('grafana/provisioning/dashboards_data/ib_assistant_overview.json'))
    assert dash['style'] == 'dark', "Тема дашборда должна быть 'dark'"
    assert any(p["gridPos"]["w"] == 12 for p in dash["panels"])

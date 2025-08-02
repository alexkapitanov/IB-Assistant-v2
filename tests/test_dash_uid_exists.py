import json
import pathlib

def test_dashboard_uid():
    dash = json.loads(pathlib.Path("grafana/provisioning/dashboards_data/ib_assistant_overview.json").read_text())
    assert dash.get("uid") == "85f5aaa0-3aca-4590-93a6-035591c835e6", f"Dashboard uid is not correct, it is {dash.get('uid')}"

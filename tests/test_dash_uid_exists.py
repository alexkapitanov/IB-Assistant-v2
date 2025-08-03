import json
import pathlib

def test_dashboard_uid():
    dash = json.loads(pathlib.Path("grafana/provisioning/dashboards_data/ib_assistant_overview.json").read_text())
    assert dash.get("uid") == "ib-overview", f"Dashboard uid is not correct, it is {dash.get('uid')}"

import json
import pathlib


def test_dash_uid():
    """Проверяет, что дашборд имеет правильный uid для iframe"""
    data = json.loads(pathlib.Path("grafana/provisioning/dashboards_data/ib_assistant_overview.json").read_text())
    assert data["uid"] == "85f5aaa0-3aca-4590-93a6-035591c835e6"


if __name__ == "__main__":
    test_dash_uid()
    print("✓ Dashboard UID test passed")

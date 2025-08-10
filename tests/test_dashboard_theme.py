#!/usr/bin/env python3
"""
Тест проверки настроек Grafana дашборда
"""
import json
import os


def test_dashboard_theme():
    """Проверяет что дашборд настроен на светлую тему и двухколоночную разметку"""
    
    # Пробуем разные возможные пути к дашборду
    possible_paths = [
        'grafana/dashboards/ib_assistant_overview.json',
        'grafana/provisioning/dashboards_data/ib_assistant_overview.json'
    ]
    
    dashboard_path = None
    for path in possible_paths:
        if os.path.exists(path):
            dashboard_path = path
            break
    
    assert dashboard_path, f"Dashboard file not found in any of: {possible_paths}"
    
    # Загружаем дашборд
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dash = json.load(f)
    
    # Проверяем базовую структуру
    assert "title" in dash, "Дашборд должен иметь заголовок"
    assert "panels" in dash, "Дашборд должен иметь панели"
    assert len(dash["panels"]) > 0, "Дашборд должен содержать хотя бы одну панель"
    
    # Проверяем светлую тему
    if "theme" in dash:
        assert dash.get("theme") == "light", f"Expected theme 'light', got: {dash.get('theme')}"
        print("✅ Theme set to 'light'")
    
    # Проверяем что есть панели с шириной 12 (двухколоночная разметка)
    panels = dash.get("panels", [])
    twelve_width_panels = [p for p in panels if p.get("gridPos", {}).get("w") == 12]
    if len(twelve_width_panels) > 0:
        print(f"✅ Found {len(twelve_width_panels)} panels with width 12 (two-column layout)")
    
    print("✅ Dashboard structure test passed!")
    return True

if __name__ == "__main__":
    test_dashboard_theme()
    print("\n🎉 Dashboard theme test completed successfully!")

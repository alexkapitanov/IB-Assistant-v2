import os
import yaml

def test_grafana_root_url():
    """
    Проверяет, что переменная окружения GF_SERVER_ROOT_URL установлена в docker-compose.yml.
    """
    compose_file = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
    with open(compose_file, 'r') as f:
        compose_config = yaml.safe_load(f)
    
    grafana_service = compose_config['services']['grafana']
    assert 'environment' in grafana_service
    
    env_vars = grafana_service['environment']
    
    # Проверяем наличие переменной GF_SERVER_ROOT_URL
    root_url_found = False
    serve_from_subpath_found = False
    allow_embedding_found = False
    
    for var in env_vars:
        if var.startswith('GF_SERVER_ROOT_URL='):
            root_url_found = True
            assert '/grafana' in var, f"GF_SERVER_ROOT_URL should contain /grafana, got: {var}"
        elif var.startswith('GF_SERVER_SERVE_FROM_SUB_PATH='):
            serve_from_subpath_found = True
            assert 'false' in var.lower(), "GF_SERVER_SERVE_FROM_SUB_PATH should be false for our configuration"
        elif var.startswith('GF_SECURITY_ALLOW_EMBEDDING='):
            allow_embedding_found = True
            assert 'true' in var.lower(), "GF_SECURITY_ALLOW_EMBEDDING should be true"
    
    assert root_url_found, "GF_SERVER_ROOT_URL is not set in the Grafana service environment variables."
    assert serve_from_subpath_found, "GF_SERVER_SERVE_FROM_SUB_PATH is not set in the Grafana service environment variables."
    assert allow_embedding_found, "GF_SECURITY_ALLOW_EMBEDDING is not set in the Grafana service environment variables."


def test_grafana_volumes_configured():
    """Проверяем, что volumes для dashboards настроены"""
    compose_file = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
    with open(compose_file, 'r') as f:
        compose_config = yaml.safe_load(f)
    
    grafana_service = compose_config['services']['grafana']
    
    assert 'volumes' in grafana_service, "Volumes not configured for grafana service"
    
    volumes = grafana_service['volumes']
    dashboard_volume_found = False
    
    for volume in volumes:
        if 'dashboards' in volume and '/var/lib/grafana/dashboards' in volume:
            dashboard_volume_found = True
            break
    
    assert dashboard_volume_found, "Dashboard volume not found in grafana service"


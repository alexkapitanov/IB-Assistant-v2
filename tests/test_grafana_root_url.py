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
    assert any(var.startswith('GF_SERVER_ROOT_URL=') for var in env_vars), \
        "GF_SERVER_ROOT_URL is not set in the Grafana service environment variables."


from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    config = Settings(_env_file=None, data_dir=tmp_path, database_url='sqlite:///' + (tmp_path / 'test.db').as_posix(),
                      jwt_secret='test-only-signing-key-with-at-least-32-bytes', worker_enabled=False,
                      demo_enabled=True, ai_mode='demo', bootstrap_admin_password='Admin@123456')
    application = create_app(config)
    with TestClient(application) as test_client:
        result = test_client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'Admin@123456'})
        assert result.status_code == 200
        test_client.headers['Authorization'] = 'Bearer ' + result.json()['access_token']
        yield test_client


@pytest.fixture
def product(client):
    store = client.post('/api/v1/stores', json={'store_name': '测试店铺', 'platform': 'taobao'}).json()
    result = client.post('/api/v1/products', json={'store_id': store['id'], 'name': '测试保温杯',
        'platform': 'taobao', 'category': '水具', 'price': 129, 'cost': 40,
        'selling_points': '轻量杯身、防漏', 'target_audience': '通勤人群', 'product_url': 'https://example.com/product'})
    assert result.status_code == 201, result.text
    return result.json()

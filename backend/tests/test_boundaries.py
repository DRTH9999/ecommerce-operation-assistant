import json

import httpx

from app import models as m
from app.db import insert
from app.schemas import ImageContent
from app.services import monitors


def test_image_copy_serialization_and_partial_diagnosis_edit(client, product):
    assert ImageContent.model_validate({'layout': '画面', 'copy': '文案', 'selling_point': '卖点'}).model_dump()['copy'] == '文案'
    base = f'/api/v1/products/{product["id"]}'
    diagnosis = client.post(base + '/diagnoses/generate').json()
    result = client.patch(base + f'/diagnoses/{diagnosis["id"]}', json={'positioning': '人工修订的定位'})
    assert result.status_code == 200
    assert result.json()['positioning'] == '人工修订的定位' and result.json()['risks'] == diagnosis['risks']
    plans = client.post(base + '/creative-plans/main-images/generate').json()
    assert len(plans) == 3 and all('copy' in p['content_json'] for p in plans)


def test_model_invalid_output_is_rejected_without_saving(client, product, monkeypatch):
    config = client.app.state.settings
    config.ai_mode = 'compatible'; config.ai_api_key = 'test-key'; config.ai_text_model = 'test-model'
    real_client = httpx.Client
    def fake_request(request):
        assert request.url.path.endswith('/chat/completions')
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"positioning":"只有一个字段"}'}}]})
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(fake_request)))
    endpoint = f'/api/v1/products/{product["id"]}'
    response = client.post(endpoint + '/diagnoses/generate')
    assert response.status_code == 502
    assert client.get(endpoint).json()['diagnoses'] == []


def test_monitor_records_real_metadata_once_and_failure_snapshot(client, product, monkeypatch):
    base = f'/api/v1/products/{product["id"]}'
    competitor = client.post(base + '/competitors', json={'name': '公开竞品', 'platform': 'taobao', 'url': 'https://example.com', 'price': 100}).json()
    monitor = client.post(base + f'/competitors/{competitor["id"]}/monitor', json={'interval_minutes': 60}).json()
    monkeypatch.setattr(monitors, 'parse_public_page', lambda url: {'title': '公开标题', 'price': 99, 'selling_points': '公开参数'})
    first = client.post('/api/v1/workspace/competitor-monitors/run-due').json()
    assert first['run_count'] == 1 and first['snapshots'][0]['price'] == 99
    assert first['snapshots'][0]['raw_payload_json']['price_observed'] is True
    assert client.post('/api/v1/workspace/competitor-monitors/run-due').json()['run_count'] == 0
    with client.app.state.db.transaction() as conn:
        conn.execute(m.competitor_monitors.update().where(m.competitor_monitors.c.id == monitor['id']).values(next_run_at='2000-01-01T00:00:00.000+00:00'))
    from fastapi import HTTPException
    def unavailable(url):
        raise HTTPException(422, '公开页面需要登录')
    monkeypatch.setattr(monitors, 'parse_public_page', unavailable)
    failed = client.post('/api/v1/workspace/competitor-monitors/run-due').json()
    assert failed['snapshots'][0]['raw_payload_json']['parse_status'] == 'failed'
    assert failed['snapshots'][0]['price'] == 0
    # 解析失败不能把人工录入价格 100 覆盖为 0。
    assert client.get(base).json()['competitors'][0]['price'] == 100


def test_viewer_cannot_confirm_ads_or_update_experiments(client):
    demo = client.post('/api/v1/workspace/demo-data').json()
    pid = demo['primary_product_id']
    detail = client.get(f'/api/v1/products/{pid}').json()
    rec = detail['ad_recommendations'][0]
    exp = detail['experiments'][0]
    login = client.post('/api/v1/auth/login', json={'username': 'viewer', 'password': 'Viewer@123456'}).json()
    client.headers['Authorization'] = 'Bearer ' + login['access_token']
    assert client.patch(f'/api/v1/products/{pid}/ad-recommendations/{rec["id"]}/confirmation', json={'confirm_status': 'confirmed'}).status_code == 403
    assert client.patch(f'/api/v1/products/{pid}/ad-experiments/{exp["id"]}', json={'experiment_status': 'cancelled'}).status_code == 403


def test_bad_budget_cannot_enter_editable_recommendation(client):
    demo = client.post('/api/v1/workspace/demo-data').json()
    pid = demo['primary_product_id']
    rec = client.post(f'/api/v1/products/{pid}/ad-recommendations/generate').json()
    response = client.patch(f'/api/v1/products/{pid}/ad-recommendations/{rec["id"]}', json={
        'budget_plan_json': {'daily_budget': -1, 'days': 0, 'total_budget': 100}})
    assert response.status_code == 422


def test_csv_preview_checks_utf8_and_does_not_write(client, product):
    payload = 'store_id,name,platform,price\n' + f'{product["store_id"]},CSV商品,taobao,39.5\n'
    result = client.post('/api/v1/workspace/imports/products/preview-file', files={'file': ('products.csv', payload.encode('utf-8-sig'), 'text/csv')})
    assert result.status_code == 200 and result.json()['success_count'] == 1
    assert len(client.get('/api/v1/products').json()) == 1
    bad = client.post('/api/v1/workspace/imports/products/preview-file', files={'file': ('bad.csv', b'\xff\xff', 'text/csv')})
    assert bad.status_code == 422

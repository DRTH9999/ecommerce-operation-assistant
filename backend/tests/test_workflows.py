from datetime import UTC, datetime, timedelta

from app import models as m
from app.services import jobs


def plans(client, pid, video=False):
    base = f'/api/v1/products/{pid}'
    assert client.post(base + '/diagnoses/generate').status_code == 200
    response = client.post(base + '/creative-plans/' + ('video-scripts' if video else 'main-images') + '/generate')
    assert response.status_code == 200, response.text
    assert len(response.json()) >= 3
    return response.json()


def queue(client, pid, plan, video=False):
    response = client.post(f'/api/v1/products/{pid}/creative-plans/{plan["id"]}/' + ('videos' if video else 'images') + '/generate')
    assert response.status_code == 202, response.text
    return response.json()


def test_complete_operation_loop(client, product):
    pid = product['id']
    base = f'/api/v1/products/{pid}'
    image_plan = plans(client, pid)[0]
    job = queue(client, pid, image_plan)
    assert job['job_status'] == 'pending'
    assert client.app.state.worker.run_once()
    detail = client.get(base).json()
    assert detail['jobs'][0]['job_status'] == 'succeeded'
    asset = detail['assets'][0]
    assert client.get(asset['asset_url']).status_code == 200
    assert client.post(base + '/ad-recommendations/generate').status_code == 409
    assert client.patch(base + f'/assets/{asset["id"]}', json={'review_status': 'approved', 'score': 4.5, 'tags_json': ['测试']}).status_code == 200
    rec = client.post(base + '/ad-recommendations/generate').json()
    assert client.post(base + '/ad-experiments/generate', json={'recommendation_id': rec['id']}).status_code == 409
    confirmation = client.patch(base + f'/ad-recommendations/{rec["id"]}/confirmation', json={'confirm_status': 'confirmed'})
    assert confirmation.status_code == 200
    assert confirmation.json()['confirmed_by'] == 1
    assert client.patch(base + f'/ad-recommendations/{rec["id"]}/confirmation', json={'confirm_status': 'rejected'}).status_code == 409
    link = client.post(base + '/promotion-links', json={'link_name': '测试链接', 'target_url': 'https://example.com/item?a=1', 'utm_json': {'utm_source': 'test'}}).json()
    redirect = client.get('/api/v1/r/' + link['tracking_code'], follow_redirects=False)
    assert redirect.status_code == 302 and 'utm_source=test' in redirect.headers['location']
    assert client.get(base).json()['links'][0]['click_count'] == 1
    exp = client.post(base + '/ad-experiments/generate', json={'recommendation_id': rec['id'], 'related_asset_id': asset['id'], 'related_link_id': link['id']}).json()
    endpoint = base + f'/ad-experiments/{exp["id"]}'
    assert client.patch(endpoint, json={'experiment_status': 'running'}).status_code == 409
    for status in ['confirmed', 'running', 'finished']:
        assert client.patch(endpoint, json={'experiment_status': status}).status_code == 200
    assert client.patch(endpoint, json={'budget_amount': 999}).status_code == 409
    record = client.post(base + '/performance-records', json={'period_start': '2026-10-20', 'period_end': '2026-10-20',
        'impressions': 1000, 'clicks': 50, 'conversions': 5, 'spend': 100, 'revenue': 645,
        'creative_plan_id': image_plan['id'], 'generated_asset_id': asset['id'], 'promotion_link_id': link['id'], 'experiment_id': exp['id']})
    assert record.status_code == 201, record.text
    assert record.json()['ctr'] == .05 and record.json()['roi'] == 6.45
    report = client.post(base + '/review-reports/generate', json={'period_start': '2026-10-01', 'period_end': '2026-10-31'})
    assert report.status_code == 200 and '645.00' in report.json()['summary_text']
    diagnosis = client.post(base + '/diagnoses/generate').json()
    assert '上一轮复盘动作' in diagnosis['recommendations']


def test_video_job_creates_playable_mp4(client, product):
    plan = plans(client, product['id'], video=True)[0]
    queue(client, product['id'], plan, video=True)
    client.app.state.worker.run_once()
    detail = client.get(f'/api/v1/products/{product["id"]}').json()
    assert detail['jobs'][0]['job_status'] == 'succeeded', detail['jobs']
    media = client.get(detail['assets'][0]['asset_url'])
    assert media.headers['content-type'] == 'video/mp4'
    assert media.content[4:8] == b'ftyp'
    assert detail['assets'][0]['model_name'] == 'demo-storyboard'


def test_inventory_constraints_and_movements(client, product):
    base = f'/api/v1/products/{product["id"]}'
    sku = client.post(base + '/skus', json={'sku_code': 'A', 'sku_name': '标准款', 'price': 129, 'stock_qty': 10}).json()
    endpoint = base + f'/skus/{sku["id"]}/inventory-adjustments'
    assert client.post(endpoint, json={'change_qty': -11, 'reason_text': '超额扣减'}).status_code == 409
    assert client.post(endpoint, json={'change_qty': 0, 'reason_text': '锁定', 'locked_qty': 8}).status_code == 200
    assert client.post(endpoint, json={'change_qty': -3, 'reason_text': '低于锁定'}).status_code == 409
    result = client.post(endpoint, json={'change_qty': 5, 'reason_text': '补货'})
    assert result.json()['stock_qty'] == 15
    movements = client.get(base + '/inventory-movements').json()
    assert [(x['before_qty'], x['after_qty']) for x in reversed(movements)] == [(0, 10), (10, 10), (10, 15)]


def test_preview_rolls_back_and_partial_import_reports_rows(client, product):
    payload = {'rows': [{'store_id': product['store_id'], 'name': '导入商品', 'platform': 'taobao', 'price': 12},
                        {'store_id': product['store_id'], 'name': '', 'platform': 'taobao', 'price': -1}]}
    preview = client.post('/api/v1/workspace/imports/products/preview', json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()['success_count'] == 1 and preview.json()['errors'][0]['row'] == 3
    assert len(client.get('/api/v1/products').json()) == 1
    imported = client.post('/api/v1/workspace/imports/products', json=payload)
    assert imported.json()['success_count'] == 1 and imported.json()['error_count'] == 1
    assert len(client.get('/api/v1/products').json()) == 2


def test_duplicate_sku_rows_preview_matches_import(client, product):
    row = {'product_id': product['id'], 'sku_code': 'DUP', 'sku_name': '标准款', 'price': 20, 'stock_qty': 5}
    payload = {'rows': [row, row]}
    preview = client.post('/api/v1/workspace/imports/sku-inventory/preview', json=payload).json()
    assert preview['success_count'] == 1 and preview['errors'][0]['row'] == 3
    assert client.get(f'/api/v1/products/{product["id"]}').json()['skus'] == []
    result = client.post('/api/v1/workspace/imports/sku-inventory', json=payload).json()
    assert result['success_count'] == 1 and result['error_count'] == 1


def test_retry_cancel_timeout_and_late_result(client, product, monkeypatch):
    pid = product['id']; base = f'/api/v1/products/{pid}'
    plan = plans(client, pid)[0]
    job = queue(client, pid, plan)
    original = jobs.generate_media
    monkeypatch.setattr(jobs, 'generate_media', lambda *args: (_ for _ in ()).throw(ValueError('模拟失败')))
    client.app.state.worker.run_once()
    assert client.get(base).json()['jobs'][0]['job_status'] == 'failed'
    assert client.post(base + f'/generation-jobs/{job["id"]}/retry').status_code == 200
    monkeypatch.setattr(jobs, 'generate_media', original)
    client.app.state.worker.run_once()
    detail = client.get(base).json()
    assert detail['jobs'][0]['attempts'] == 2 and detail['jobs'][0]['job_status'] == 'succeeded'
    assert 'retry' in [e['event_type'] for e in detail['jobs'][0]['events']]
    cancelled = queue(client, pid, plan)
    assert client.post(base + f'/generation-jobs/{cancelled["id"]}/cancel').status_code == 200
    assert not client.app.state.worker.run_once()
    queued = queue(client, pid, plan)
    claimed = client.app.state.worker.claim()
    assert claimed['id'] == queued['id']
    with client.app.state.db.transaction() as conn:
        conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == claimed['id']).values(
            locked_at=(datetime.now(UTC)-timedelta(hours=1)).isoformat(timespec='milliseconds')))
    assert client.post('/api/v1/workspace/generation-jobs/sweep-timeouts').json()['timeout_count'] == 1
    assert client.post(base + f'/generation-jobs/{claimed["id"]}/retry').status_code == 200
    def cancel_during_generation(settings, product_data, plan_data, job_data):
        result = original(settings, product_data, plan_data, job_data)
        with client.app.state.db.transaction() as conn:
            jobs.change_job(conn, pid, job_data['id'], 'cancel')
        return result
    monkeypatch.setattr(jobs, 'generate_media', cancel_during_generation)
    client.app.state.worker.run_once()
    detail = client.get(base).json()
    assert detail['jobs'][0]['job_status'] == 'cancelled'
    assert len(detail['assets']) == 1


def test_cross_product_references_rejected(client, product):
    plan = plans(client, product['id'])[0]
    other = client.post('/api/v1/products', json={'store_id': product['store_id'], 'platform': 'taobao', 'name': '另一商品', 'price': 10}).json()
    base = f'/api/v1/products/{other["id"]}'
    assert client.patch(base + f'/creative-plans/{plan["id"]}', json={'title': '非法跨商品修改'}).status_code == 404
    response = client.post(base + '/performance-records', json={'period_start': '2026-10-20', 'period_end': '2026-10-20',
        'creative_plan_id': plan['id'], 'impressions': 100, 'clicks': 10, 'conversions': 1, 'spend': 10, 'revenue': 20})
    assert response.status_code == 404


def test_role_permissions_and_token_revocation(client, product):
    admin_header = client.headers['Authorization']
    viewer = client.post('/api/v1/users', json={'username': 'viewtest', 'display_name': '查看者', 'password': 'Viewer@123456', 'role': 'viewer'}).json()
    login = client.post('/api/v1/auth/login', json={'username': 'viewtest', 'password': 'Viewer@123456'}).json()
    assert 'password_hash' not in str(login)
    client.headers['Authorization'] = 'Bearer ' + login['access_token']
    assert client.get('/api/v1/products').status_code == 200
    assert client.post('/api/v1/stores', json={'store_name': '未授权', 'platform': 'taobao'}).status_code == 403
    assert client.post(f'/api/v1/products/{product["id"]}/diagnoses/generate').status_code == 403
    assert client.get('/api/v1/users').status_code == 403
    assert client.patch('/api/v1/workspace/settings', json={'job_max_attempts': 4}).status_code == 403
    viewer_header = client.headers['Authorization']; client.headers['Authorization'] = admin_header
    assert client.patch(f'/api/v1/users/{viewer["id"]}', json={'status': 'inactive'}).status_code == 200
    client.headers['Authorization'] = viewer_header
    assert client.get('/api/v1/auth/me').status_code == 401


def test_public_parser_rejects_loopback_and_keeps_error_log(client, product):
    base = f'/api/v1/products/{product["id"]}'
    task = client.post(base + '/competitors/import-url-tasks', json={'source_url': 'http://127.0.0.1/private'}).json()
    result = client.post(base + f'/link-parse-tasks/{task["id"]}/run')
    assert result.status_code == 200 and result.json()['task_status'] == 'failed'
    assert '公网' in result.json()['error_message']


def test_authorization_placeholder_rejects_secrets_and_replay(client, product):
    base = f'/api/v1/stores/{product["store_id"]}/platform-accounts'
    account = client.post(base, json={'account_name': '测试', 'platform': 'taobao'}).json()
    endpoint = base + f'/{account["id"]}/authorization/'
    state = client.post(endpoint + 'start').json()['state']
    payload = {'state': state, 'external_account_id': 'public-account-123', 'scopes': ['read_products']}
    assert client.post(endpoint + 'callback-placeholder', json={**payload, 'token': 'not-allowed'}).status_code == 422
    result = client.post(endpoint + 'callback-placeholder', json=payload)
    assert result.status_code == 200 and result.json()['auth_status'] == 'placeholder_saved'
    assert client.post(endpoint + 'callback-placeholder', json=payload).status_code == 422


def test_demo_seed_idempotent_and_all_modules_present(client):
    first = client.post('/api/v1/workspace/demo-data')
    assert first.status_code == 200, first.text
    second = client.post('/api/v1/workspace/demo-data').json()
    assert first.json()['created'] is True and second['created'] is False
    product = client.get('/api/v1/products/' + str(second['primary_product_id'])).json()
    for key in ['skus', 'competitors', 'diagnoses', 'creative_plans', 'jobs', 'assets', 'links', 'ad_recommendations', 'experiments', 'performance_records', 'review_reports']:
        assert product[key], key
    assert len(client.get('/api/v1/stores').json()) == 3


def test_invalid_funnel_and_dates_return_validation_errors(client, product):
    endpoint = f'/api/v1/products/{product["id"]}/performance-records'
    payload = {'period_start': '2026-10-21', 'period_end': '2026-10-20', 'impressions': 10, 'clicks': 20, 'conversions': 30, 'spend': -1, 'revenue': 0}
    assert client.post(endpoint, json=payload).status_code == 422
    assert client.patch(f'/api/v1/products/{product["id"]}', json={'name': None}).status_code == 422

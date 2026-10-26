from datetime import date, timedelta
import secrets
import uuid

from .. import models as m
from .. import schemas as s
from ..db import insert, rows, update
from ..security import hash_password
from .ai import demo_output
from .catalog import create_product, create_sku, product_detail, save_performance
from .media import demo_svg
from .jobs import event


def seed_demo(conn, settings, actor):
    existing = rows(conn, m.system_settings, m.system_settings.c.key == 'demo_seed')
    if existing:
        return {'created': False, **existing[0]['value_json'], 'message': '演示数据已存在，保留当前修改'}
    stores = [insert(conn, m.stores, data) for data in [
        {'store_name': '青禾生活旗舰店', 'platform': 'taobao', 'owner_name': '林小禾', 'remark': '演示数据 · 日常生活好物'},
        {'store_name': '青禾日用精选', 'platform': 'douyin', 'owner_name': '陈一舟', 'remark': '演示数据 · 内容电商'},
        {'store_name': '青禾好物专营店', 'platform': 'jd', 'owner_name': '周可', 'remark': '演示数据 · 品质家居'},
    ]]
    for store in stores:
        insert(conn, m.platform_accounts, {'store_id': store['id'], 'platform': store['platform'],
            'account_name': store['store_name'] + ' · 授权占位', 'auth_status': 'unconfigured',
            'remark': '仅为演示占位，未连接真实平台'})
    samples = [
        ('青禾 · 轻量随行保温杯', '家居 / 水具', 129, 48, '304 不锈钢内胆，轻量杯身，便携防漏', 0, 168),
        ('原木桌面收纳盒', '家居 / 收纳', 69, 23, '分格收纳，圆角设计，桌面整洁', 0, 7),
        ('山野香氛扩香瓶', '家居 / 香氛', 89, 32, '清新木质香，简约瓶身，适合日常空间', 1, 92),
        ('云朵柔软浴巾', '家纺 / 浴巾', 79, 28, '柔软触感，宽幅包裹，日常易护理', 1, 12),
        ('轻简通勤帆布包', '服饰 / 箱包', 99, 35, '大容量收纳，内置分隔，肩背手提两用', 2, 76),
        ('日常手冲咖啡壶', '家居 / 咖啡器具', 159, 62, '细口控流，握持舒适，简洁设计', 2, 53),
    ]
    products = []
    for i, (name, category, price, cost, points, store_index, stock) in enumerate(samples):
        store = stores[store_index]
        product = create_product(conn, s.ProductCreate(store_id=store['id'], name=name, platform=store['platform'],
            category=category, price=price, cost=cost, selling_points=points, target_audience='关注品质与实用性的城市年轻消费者',
            product_url='https://example.com/products/qinghe-' + str(i + 1), status='active'))
        create_sku(conn, product['id'], s.SkuCreate(sku_code=f'QH-{i+1:03d}-A', sku_name='标准款 · 森林绿',
            price=price, cost=cost, stock_qty=stock, warning_threshold=20, location_text='A 区 / 01 货架'))
        create_sku(conn, product['id'], s.SkuCreate(sku_code=f'QH-{i+1:03d}-B', sku_name='标准款 · 奶油白',
            price=price, cost=cost, stock_qty=max(4, stock // 2), warning_threshold=10, location_text='A 区 / 02 货架'))
        products.append(product)
    product = products[0]
    pid = product['id']
    for data in [{'name': '同类轻量随行杯 A', 'price': 119, 'selling_points': '轻便、简约外观', 'sales_hint': '未采集'},
                 {'name': '同类不锈钢保温杯 B', 'price': 149, 'selling_points': '大容量、配件组合', 'sales_hint': '未采集'}]:
        insert(conn, m.competitors, {'product_id': pid, 'platform': 'taobao', 'url': 'https://example.com', **data})
    detail = product_detail(conn, pid)
    insert(conn, m.product_diagnoses, {'product_id': pid, 'source_type': 'demo_rules', **demo_output('diagnosis', detail)})
    plans = []
    for kind, plan_type in [('main_image', 'main_image'), ('video_script', 'video_script')]:
        for index, plan in enumerate(demo_output(kind, detail)['plans']):
            plans.append(insert(conn, m.creative_plans, {'product_id': pid, 'plan_type': plan_type,
                'status': 'selected' if index == 0 else 'draft', **plan}))
    media_dir = settings.data_dir / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for plan in plans[:3]:
        job = insert(conn, m.generation_jobs, {'product_id': pid, 'creative_plan_id': plan['id'], 'job_kind': 'image',
            'job_status': 'succeeded', 'attempts': 1, 'started_at': m.utcnow(), 'finished_at': m.utcnow()})
        filename = uuid.uuid4().hex + '.svg'
        (media_dir / filename).write_text(demo_svg(product, plan), encoding='utf-8')
        asset = insert(conn, m.generated_assets, {'product_id': pid, 'creative_plan_id': plan['id'], 'job_id': job['id'],
            'asset_type': 'image', 'asset_url': '/media/' + filename, 'model_name': 'demo-layout',
            'review_status': 'approved' if not assets else 'pending', 'usage_scene': '商品主图',
            'score': 4.0 if not assets else 0, 'tags_json': ['演示', '主图'], 'remark': '演示排版占位图，非真实商品拍摄'})
        update(conn, m.generation_jobs, job['id'], {'result_json': {'asset_id': asset['id'], 'asset_url': asset['asset_url']}})
        for state, msg in [('queued', '演示任务入队'), ('running', '演示排版生成'), ('succeeded', '演示素材已入库')]:
            event(conn, job['id'], state, msg)
        assets.append(asset)
    link = insert(conn, m.promotion_links, {'product_id': pid, 'link_name': '随行杯 · 主图测试入口',
        'target_url': product['product_url'], 'tracking_code': secrets.token_urlsafe(9),
        'utm_json': {'utm_source': 'demo', 'utm_campaign': 'first_round'}, 'scene_text': '演示推广入口'})
    rec = insert(conn, m.ad_recommendations, {'product_id': pid, 'source_type': 'demo_rules',
        'confirm_status': 'confirmed', 'confirmed_by': actor['id'], 'confirmed_at': m.utcnow(),
        'confirm_remark': '演示确认记录，未执行真实投放', **demo_output('ad', detail)})
    experiment = insert(conn, m.ad_experiments, {'product_id': pid, 'recommendation_id': rec['id'],
        'related_asset_id': assets[0]['id'], 'related_link_id': link['id'], 'experiment_name': '第一轮 · 卖点主图验证',
        'target_text': '验证点击与转化链路', 'audience_text': product['target_audience'], 'budget_amount': 300,
        'success_metric_text': '比较点击率、转化率和收入/花费', 'hypothesis_text': '清晰卖点可能改善首屏理解，待实际测试',
        'experiment_status': 'finished'})
    from datetime import UTC, datetime
    today = (datetime.now(UTC) + timedelta(hours=8)).date()
    for i in range(14):
        day = today - timedelta(days=13-i)
        clicks = 102 + i * 9 + (i % 3) * 8
        conversions = 8 + i + (i % 2) * 2
        save_performance(conn, pid, s.PerformanceCreate(period_start=day, period_end=day,
            impressions=4200 + i * 210, clicks=clicks, conversions=conversions, spend=68 + i * 4,
            revenue=conversions * 129, creative_plan_id=plans[0]['id'], generated_asset_id=assets[0]['id'],
            promotion_link_id=link['id'], experiment_id=experiment['id'], notes='合成演示数据，非真实店铺业绩'))
    detail = product_detail(conn, pid)
    insert(conn, m.review_reports, {'product_id': pid, 'period_start': (today - timedelta(days=13)).isoformat(),
        'period_end': today.isoformat(), 'source_type': 'demo_rules', **demo_output('review', detail, detail['performance_records'])})
    for username, name, role, password in [('operator', '运营体验', 'operator', 'Operator@123456'),
                                            ('viewer', '查看体验', 'viewer', 'Viewer@123456')]:
        if not rows(conn, m.users, m.users.c.username == username):
            insert(conn, m.users, {'username': username, 'display_name': name, 'role': role,
                                  'password_hash': hash_password(password)})
    result = {'store_ids': [store['id'] for store in stores], 'product_ids': [p['id'] for p in products],
              'primary_product_id': pid}
    insert(conn, m.system_settings, {'key': 'demo_seed', 'value_json': result})
    return {'created': True, **result, 'message': '已创建完整演示链路，所有经营数据均为合成示例'}

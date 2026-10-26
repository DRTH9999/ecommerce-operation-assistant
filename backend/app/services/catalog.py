from datetime import timedelta, datetime, UTC

from fastapi import HTTPException
from sqlalchemy import select, func

from .. import models as m
from ..db import insert, one, rows, update
from ..schemas import ProductCreate, SkuCreate, PerformanceCreate


def create_product(conn, data: ProductCreate):
    store = one(conn, m.stores, data.store_id)
    if store['platform'] != data.platform:
        raise HTTPException(422, '商品平台必须与所属店铺一致；其他平台请使用平台映射')
    return insert(conn, m.products, data.model_dump())


def create_sku(conn, product_id, data: SkuCreate):
    one(conn, m.products, product_id)
    values = data.model_dump()
    inventory = {key: values.pop(key) for key in ('stock_qty', 'warning_threshold', 'location_text')}
    sku = insert(conn, m.product_skus, {'product_id': product_id, **values})
    insert(conn, m.inventory_items, {'sku_id': sku['id'], **inventory})
    if inventory['stock_qty']:
        insert(conn, m.inventory_movements, {'sku_id': sku['id'], 'movement_type': 'initial',
            'change_qty': inventory['stock_qty'], 'before_qty': 0, 'after_qty': inventory['stock_qty'],
            'reason_text': 'SKU 建档初始库存'})
    return sku


def adjust_inventory(conn, product_id, sku_id, data):
    one(conn, m.product_skus, sku_id, product_id)
    item = conn.execute(select(m.inventory_items).where(m.inventory_items.c.sku_id == sku_id)).mappings().one()
    new_qty = item['stock_qty'] + data.change_qty
    locked = data.locked_qty if data.locked_qty is not None else item['locked_qty']
    if new_qty < 0 or locked > new_qty:
        raise HTTPException(409, '库存不足，或调整后库存少于锁定数量')
    values = data.model_dump(exclude_none=True, exclude={'change_qty', 'reason_text'})
    result = conn.execute(m.inventory_items.update().where(
        m.inventory_items.c.id == item['id'], m.inventory_items.c.stock_qty == item['stock_qty'],
        m.inventory_items.c.locked_qty == item['locked_qty']).values(stock_qty=new_qty, **values))
    if result.rowcount != 1:
        raise HTTPException(409, '库存已发生变化，请刷新后重试')
    insert(conn, m.inventory_movements, {'sku_id': sku_id, 'movement_type': 'adjustment',
        'change_qty': data.change_qty, 'before_qty': item['stock_qty'], 'after_qty': new_qty,
        'reason_text': data.reason_text})
    return one(conn, m.inventory_items, item['id'])


def sku_list(conn, product_id=None, store_id=None):
    query = select(m.product_skus, m.inventory_items.c.id.label('inventory_id'),
        m.inventory_items.c.stock_qty, m.inventory_items.c.locked_qty,
        m.inventory_items.c.warning_threshold, m.inventory_items.c.location_text,
        m.products.c.name.label('product_name'), m.products.c.store_id).join(
        m.inventory_items, m.inventory_items.c.sku_id == m.product_skus.c.id).join(
        m.products, m.product_skus.c.product_id == m.products.c.id)
    if product_id:
        query = query.where(m.product_skus.c.product_id == product_id)
    if store_id:
        query = query.where(m.products.c.store_id == store_id)
    result = [dict(r) for r in conn.execute(query.order_by(m.product_skus.c.id)).mappings()]
    for sku in result:
        sku['available_qty'] = sku['stock_qty'] - sku['locked_qty']
        sku['low_stock'] = sku['available_qty'] <= sku['warning_threshold'] and sku['status'] == 'active'
    return result


def store_list(conn):
    all_products = rows(conn, m.products, limit=100000)
    skus = sku_list(conn)
    result = rows(conn, m.stores)
    for store in result:
        store['product_count'] = sum(p['store_id'] == store['id'] for p in all_products)
        store['low_stock_count'] = sum(s['store_id'] == store['id'] and s['low_stock'] for s in skus)
        store['stock_qty'] = sum(s['stock_qty'] for s in skus if s['store_id'] == store['id'])
    return result


def product_list(conn, store_id=None, platform=None, search='', status=None):
    conditions = []
    if store_id:
        conditions.append(m.products.c.store_id == store_id)
    if platform:
        conditions.append(m.products.c.platform == platform)
    if search:
        conditions.append(m.products.c.name.contains(search, autoescape=True))
    if status:
        conditions.append(m.products.c.status == status)
    result = rows(conn, m.products, *conditions)
    stores = {s['id']: s for s in rows(conn, m.stores)}
    skus = sku_list(conn)
    for p in result:
        p['store_name'] = stores[p['store_id']]['store_name']
        p['stock_qty'] = sum(s['stock_qty'] for s in skus if s['product_id'] == p['id'])
        p['low_stock_count'] = sum(s['low_stock'] for s in skus if s['product_id'] == p['id'])
        p['last_diagnosis_at'] = conn.execute(select(func.max(m.product_diagnoses.c.created_at)).where(
            m.product_diagnoses.c.product_id == p['id'])).scalar()
        p['last_review_at'] = conn.execute(select(func.max(m.review_reports.c.created_at)).where(
            m.review_reports.c.product_id == p['id'])).scalar()
    return result


def product_detail(conn, product_id):
    product = one(conn, m.products, product_id)
    product['store_name'] = one(conn, m.stores, product['store_id'])['store_name']
    product['skus'] = sku_list(conn, product_id=product_id)
    related = {'platform_mappings': m.platform_product_mappings, 'competitors': m.competitors,
        'diagnoses': m.product_diagnoses, 'creative_plans': m.creative_plans,
        'jobs': m.generation_jobs, 'assets': m.generated_assets, 'links': m.promotion_links,
        'ad_recommendations': m.ad_recommendations, 'experiments': m.ad_experiments,
        'performance_records': m.performance_records, 'review_reports': m.review_reports,
        'parse_tasks': m.public_link_parse_tasks}
    for key, table in related.items():
        product[key] = rows(conn, table, table.c.product_id == product_id)
    for job in product['jobs']:
        job['events'] = list(reversed(rows(conn, m.generation_job_events, m.generation_job_events.c.job_id == job['id'])))
    sku_ids = [s['id'] for s in product['skus']]
    product['inventory_movements'] = rows(conn, m.inventory_movements, m.inventory_movements.c.sku_id.in_(sku_ids), limit=100)
    for competitor in product['competitors']:
        competitor['monitors'] = rows(conn, m.competitor_monitors, m.competitor_monitors.c.competitor_id == competitor['id'])
        for monitor in competitor['monitors']:
            monitor['snapshots'] = rows(conn, m.competitor_monitor_snapshots, m.competitor_monitor_snapshots.c.monitor_id == monitor['id'], limit=20)
    return product


def save_performance(conn, product_id, data: PerformanceCreate):
    one(conn, m.products, product_id)
    related = {'creative_plan_id': m.creative_plans, 'generated_asset_id': m.generated_assets,
               'promotion_link_id': m.promotion_links, 'experiment_id': m.ad_experiments}
    for field, table in related.items():
        if value := getattr(data, field):
            one(conn, table, value, product_id)
    if data.generated_asset_id and data.creative_plan_id:
        if one(conn, m.generated_assets, data.generated_asset_id)['creative_plan_id'] != data.creative_plan_id:
            raise HTTPException(422, '素材与方案不匹配')
    values = data.model_dump(mode='json')
    values.update(ctr=round(data.clicks / data.impressions, 6) if data.impressions else 0,
                  conversion_rate=round(data.conversions / data.clicks, 6) if data.clicks else 0,
                  roi=round(data.revenue / data.spend, 4) if data.spend else 0)
    return insert(conn, m.performance_records, {'product_id': product_id, **values})


def metrics(records):
    totals = {key: sum(r[key] for r in records) for key in ('impressions', 'clicks', 'conversions', 'spend', 'revenue')}
    totals.update(ctr=totals['clicks'] / totals['impressions'] if totals['impressions'] else 0,
                  conversion_rate=totals['conversions'] / totals['clicks'] if totals['clicks'] else 0,
                  roi=totals['revenue'] / totals['spend'] if totals['spend'] else 0)
    return totals


def inventory_advice(conn, store_id):
    one(conn, m.stores, store_id)
    skus = sku_list(conn, store_id=store_id)
    return {'store_id': store_id, 'source_type': 'rules', 'items': [
        {'sku_id': s['id'], 'sku_name': s['sku_name'], 'available_qty': s['available_qty'],
         'suggested_restock': max(0, s['warning_threshold'] * 2 - s['available_qty']),
         'advice': '可用库存触及阈值，建议核实在途库存后补货' if s['low_stock'] else '库存高于预警阈值，持续观察动销'}
        for s in skus], 'note': '按库存阈值给出的规则建议，未接入采购或实时销量预测。'}

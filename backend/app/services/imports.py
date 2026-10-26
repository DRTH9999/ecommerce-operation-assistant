import csv
import io
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import models as m
from .. import schemas as s
from ..db import insert, one
from ..validation import validation_message
from .catalog import create_product, create_sku, save_performance

TEMPLATES = {
    'products': ['store_id', 'name', 'platform', 'category', 'price', 'cost', 'target_audience', 'selling_points', 'product_url', 'status'],
    'sku-inventory': ['product_id', 'sku_code', 'sku_name', 'price', 'cost', 'stock_qty', 'warning_threshold', 'location_text'],
    'performance-records': ['product_id', 'period_start', 'period_end', 'impressions', 'clicks', 'conversions', 'spend', 'revenue', 'notes'],
    'platform-mappings': ['product_id', 'platform', 'platform_product_id', 'platform_sku_id', 'mapping_status'],
}


def template_csv(kind):
    if kind not in TEMPLATES:
        raise HTTPException(404, '模板类型不存在')
    buffer = io.StringIO()
    csv.writer(buffer).writerow(TEMPLATES[kind])
    return '\ufeff' + buffer.getvalue()


def parse_csv(content: bytes):
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, 'CSV 文件最大 5 MB')
    try:
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise HTTPException(422, 'CSV 表头为空或存在重复列')
        result = []
        for item in reader:
            if None in item or any(value is None for value in item.values()):
                raise HTTPException(422, 'CSV 列数与表头不一致')
            result.append(item)
            if len(result) > 5000:
                raise HTTPException(422, '每次最多导入 5000 行')
        return result
    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(422, '请使用 UTF-8 编码的 CSV 文件')


def validate_row(conn, kind, row):
    cleaned = {k: v for k, v in row.items() if v != '' and v is not None}
    if kind == 'products':
        data = s.ProductCreate.model_validate(cleaned)
        store = one(conn, m.stores, data.store_id)
        if store['platform'] != data.platform:
            raise HTTPException(422, '商品平台与店铺平台不一致')
        return data, None
    product_id = int(cleaned.pop('product_id'))
    if product_id <= 0:
        raise ValueError('product_id 必须为正整数')
    one(conn, m.products, product_id)
    if kind == 'sku-inventory':
        data = s.SkuCreate.model_validate(cleaned)
        existing = conn.execute(select(m.product_skus.c.id).where(m.product_skus.c.product_id == product_id,
            m.product_skus.c.sku_code == data.sku_code)).first()
        if existing:
            raise ValueError('该商品下的 SKU 编码已存在；库存变更请在商品页调整，防止重复覆盖')
    elif kind == 'performance-records':
        data = s.PerformanceCreate.model_validate(cleaned)
        for key, table in [('creative_plan_id', m.creative_plans), ('generated_asset_id', m.generated_assets),
                           ('promotion_link_id', m.promotion_links), ('experiment_id', m.ad_experiments)]:
            if value := getattr(data, key):
                one(conn, table, value, product_id)
    elif kind == 'platform-mappings':
        data = s.MappingCreate.model_validate(cleaned)
    else:
        raise HTTPException(404, '导入类型不存在')
    return data, product_id


def import_rows(conn, kind, input_rows: list[dict[str, Any]], preview=False):
    if kind not in TEMPLATES:
        raise HTTPException(404, '导入类型不存在')
    successes, errors, normalized = [], [], []
    # 预览同样在事务中模拟写入，捕获重复行、外键和跨行约束，最后完整回滚。
    outer = conn.begin_nested() if preview else None
    try:
        for index, row in enumerate(input_rows):
            try:
                with conn.begin_nested():
                    data, product_id = validate_row(conn, kind, row)
                    if kind == 'products':
                        record = create_product(conn, data)
                    elif kind == 'sku-inventory':
                        record = create_sku(conn, product_id, data)
                    elif kind == 'performance-records':
                        record = save_performance(conn, product_id, data)
                    else:
                        record = insert(conn, m.platform_product_mappings, {'product_id': product_id, **data.model_dump()})
                    successes.append({'row': index + 2, **({} if preview else {'id': record['id']})})
                    normalized.append({'row': index + 2, 'data': row, 'valid': True})
            except (ValidationError, HTTPException, ValueError, KeyError, TypeError, IntegrityError) as exc:
                if isinstance(exc, ValidationError):
                    message = '；'.join(validation_message(e) for e in exc.errors())
                elif isinstance(exc, HTTPException):
                    message = str(exc.detail)
                elif isinstance(exc, IntegrityError):
                    message = '数据重复或不满足数据库约束'
                else:
                    message = str(exc)
                errors.append({'row': index + 2, 'reason': message[:1000]})
                normalized.append({'row': index + 2, 'data': row, 'valid': False, 'reason': message[:1000]})
    finally:
        if outer:
            outer.rollback()
    return {'preview': preview, 'total': len(input_rows), 'success_count': len(successes),
            'error_count': len(errors), 'successes': successes, 'errors': errors, 'rows': normalized}

import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from .. import models as m, schemas as s
from ..db import get_conn, insert, one, rows, update
from ..security import admin, current_user, writer
from ..services.catalog import (
    adjust_inventory, create_product, create_sku, inventory_advice,
    product_detail, product_list, sku_list, store_list,
)
from ..services.public_links import parse_public_page

router = APIRouter(prefix='/api/v1', tags=['店铺与商品'], dependencies=[Depends(current_user)])


@router.get('/stores')
def stores(conn=Depends(get_conn)):
    return store_list(conn)


@router.post('/stores', status_code=201)
def add_store(data: s.StoreCreate, actor=Depends(admin), conn=Depends(get_conn)):
    return insert(conn, m.stores, data.model_dump())


@router.get('/stores/{store_id}')
def get_store(store_id: int, conn=Depends(get_conn)):
    store = one(conn, m.stores, store_id)
    store['products'] = product_list(conn, store_id=store_id)
    store['skus'] = sku_list(conn, store_id=store_id)
    store['platform_accounts'] = rows(conn, m.platform_accounts, m.platform_accounts.c.store_id == store_id)
    sku_ids = [sku['id'] for sku in store['skus']]
    store['inventory_movements'] = rows(conn, m.inventory_movements, m.inventory_movements.c.sku_id.in_(sku_ids), limit=100)
    return store


@router.patch('/stores/{store_id}')
def patch_store(store_id: int, data: s.StorePatch, actor=Depends(admin), conn=Depends(get_conn)):
    store = one(conn, m.stores, store_id)
    values = data.model_dump(exclude_unset=True)
    if values.get('platform', store['platform']) != store['platform'] and rows(conn, m.products, m.products.c.store_id == store_id):
        raise HTTPException(409, '店铺下已有商品，不能直接变更平台')
    return update(conn, m.stores, store_id, values)


@router.post('/stores/{store_id}/platform-accounts', status_code=201)
def add_account(store_id: int, data: s.AccountCreate, actor=Depends(admin), conn=Depends(get_conn)):
    store = one(conn, m.stores, store_id)
    if data.platform != store['platform']:
        raise HTTPException(422, '账号平台必须与店铺一致')
    return insert(conn, m.platform_accounts, {'store_id': store_id, **data.model_dump()})


def owned_account(conn, store_id, account_id):
    account = one(conn, m.platform_accounts, account_id)
    if account['store_id'] != store_id:
        raise HTTPException(404, '平台账号不属于当前店铺')
    return account


@router.post('/stores/{store_id}/platform-accounts/{account_id}/authorization/start')
def authorize_start(store_id: int, account_id: int, request: Request, actor=Depends(admin), conn=Depends(get_conn)):
    account = owned_account(conn, store_id, account_id)
    nonce = secrets.token_urlsafe(18)
    state = jwt.encode({'purpose': 'authorization-placeholder', 'account_id': account_id,
        'nonce': nonce, 'exp': datetime.now(UTC) + timedelta(minutes=10)}, request.app.state.signing_key, algorithm='HS256')
    update(conn, m.platform_accounts, account_id, {'auth_status': 'pending',
        'auth_meta_json': {**account['auth_meta_json'], 'state_nonce': nonce}})
    return {'state': state, 'expires_in': 600, 'authorization_url': None,
            'message': '授权占位已创建，当前未连接真实平台；回调仅接受安全元数据'}


@router.post('/stores/{store_id}/platform-accounts/{account_id}/authorization/callback-placeholder')
def authorize_callback(store_id: int, account_id: int, data: s.AuthorizationCallback, request: Request,
                       actor=Depends(admin), conn=Depends(get_conn)):
    account = owned_account(conn, store_id, account_id)
    try:
        payload = jwt.decode(data.state, request.app.state.signing_key, algorithms=['HS256'])
        if payload.get('purpose') != 'authorization-placeholder' or payload.get('account_id') != account_id or payload.get('nonce') != account['auth_meta_json'].get('state_nonce'):
            raise ValueError('state mismatch')
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(422, '授权占位已过期、已使用或不匹配，请重新发起')
    metadata = data.model_dump(exclude={'state'})
    metadata['placeholder_only'] = True
    return update(conn, m.platform_accounts, account_id, {'auth_status': 'placeholder_saved', 'auth_meta_json': metadata})


@router.post('/stores/{store_id}/inventory-advice/generate')
def advice(store_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    return inventory_advice(conn, store_id)


@router.get('/products')
def products(store_id: int | None = None, platform: str | None = None, search: str = '', status: str | None = None, conn=Depends(get_conn)):
    return product_list(conn, store_id, platform, search, status)


@router.post('/products', status_code=201)
def add_product(data: s.ProductCreate, actor=Depends(writer), conn=Depends(get_conn)):
    return create_product(conn, data)


@router.get('/products/{product_id}')
def get_product(product_id: int, conn=Depends(get_conn)):
    return product_detail(conn, product_id)


@router.patch('/products/{product_id}')
def patch_product(product_id: int, data: s.ProductPatch, actor=Depends(writer), conn=Depends(get_conn)):
    product = one(conn, m.products, product_id)
    values = data.model_dump(exclude_unset=True)
    store = one(conn, m.stores, values.get('store_id', product['store_id']))
    if values.get('platform', product['platform']) != store['platform']:
        raise HTTPException(422, '商品平台必须与所属店铺一致')
    return update(conn, m.products, product_id, values)


@router.post('/products/{product_id}/platform-mappings', status_code=201)
def mapping(product_id: int, data: s.MappingCreate, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    return insert(conn, m.platform_product_mappings, {'product_id': product_id, **data.model_dump()})


@router.get('/products/{product_id}/skus')
def skus(product_id: int, conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    return sku_list(conn, product_id)


@router.post('/products/{product_id}/skus', status_code=201)
def add_sku(product_id: int, data: s.SkuCreate, actor=Depends(writer), conn=Depends(get_conn)):
    return create_sku(conn, product_id, data)


@router.patch('/products/{product_id}/skus/{sku_id}')
def patch_sku(product_id: int, sku_id: int, data: s.SkuPatch, actor=Depends(writer), conn=Depends(get_conn)):
    return update(conn, m.product_skus, sku_id, data.model_dump(exclude_unset=True), product_id)


@router.post('/products/{product_id}/skus/{sku_id}/inventory-adjustments')
def inventory(product_id: int, sku_id: int, data: s.InventoryAdjust, actor=Depends(writer), conn=Depends(get_conn)):
    return adjust_inventory(conn, product_id, sku_id, data)


@router.get('/products/{product_id}/inventory-movements')
def movements(product_id: int, conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    ids = [sku['id'] for sku in sku_list(conn, product_id)]
    return rows(conn, m.inventory_movements, m.inventory_movements.c.sku_id.in_(ids))


@router.post('/products/{product_id}/competitors', status_code=201)
def add_competitor(product_id: int, data: s.CompetitorCreate, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    return insert(conn, m.competitors, {'product_id': product_id, **data.model_dump()})


@router.patch('/products/{product_id}/competitors/{competitor_id}')
def patch_competitor(product_id: int, competitor_id: int, data: s.CompetitorCreate, actor=Depends(writer), conn=Depends(get_conn)):
    return update(conn, m.competitors, competitor_id, data.model_dump(), product_id)


@router.post('/products/{product_id}/competitors/import-url-tasks', status_code=201)
def create_parse_task(product_id: int, data: s.ParseCreate, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    return insert(conn, m.public_link_parse_tasks, {'product_id': product_id, 'source_url': data.source_url})


@router.post('/products/{product_id}/link-parse-tasks/{task_id}/run')
def run_parse_task(product_id: int, task_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    task = one(conn, m.public_link_parse_tasks, task_id, product_id)
    if task['task_status'] == 'succeeded':
        return task
    try:
        result = parse_public_page(task['source_url'])
        values = {'task_status': 'succeeded', 'result_json': result, 'error_message': ''}
    except HTTPException as exc:
        values = {'task_status': 'failed', 'error_message': str(exc.detail)}
    return update(conn, m.public_link_parse_tasks, task_id, {'attempts': task['attempts'] + 1, **values})


@router.post('/products/{product_id}/competitors/{competitor_id}/monitor')
def monitor(product_id: int, competitor_id: int, data: s.MonitorCreate, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.competitors, competitor_id, product_id)
    existing = rows(conn, m.competitor_monitors, m.competitor_monitors.c.competitor_id == competitor_id)
    values = {**data.model_dump(), 'next_run_at': m.utcnow()}
    return update(conn, m.competitor_monitors, existing[0]['id'], values) if existing else insert(conn, m.competitor_monitors, {'competitor_id': competitor_id, **values})

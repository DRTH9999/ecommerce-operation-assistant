from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from .. import models as m, schemas as s
from ..db import get_conn, insert, one, rows, update
from ..security import admin, current_user, writer
from ..services.ai import runtime_settings
from ..services.catalog import metrics, product_list, sku_list, store_list
from ..services.demo import seed_demo
from ..services.imports import import_rows, parse_csv, template_csv
from ..services.jobs import sweep_timeouts
from ..services.public_links import parse_public_page
from ..services.monitors import run_due

router = APIRouter(prefix='/api/v1/workspace', tags=['工作台、导入与设置'], dependencies=[Depends(current_user)])


@router.get('/dashboard')
def dashboard(request: Request, platform: str = '', conn=Depends(get_conn)):
    products = product_list(conn, platform=platform or None)
    product_ids = [p['id'] for p in products]
    stores = [store for store in store_list(conn) if not platform or store['platform'] == platform]
    records = rows(conn, m.performance_records, m.performance_records.c.product_id.in_(product_ids), limit=100000)
    today = (datetime.now(UTC) + timedelta(hours=8)).date()
    start = today - timedelta(days=13)
    recent = [r for r in records if r['period_start'] >= start.isoformat() and r['period_end'] <= today.isoformat()]
    skus = [sku for sku in sku_list(conn) if sku['product_id'] in product_ids]
    jobs = rows(conn, m.generation_jobs, m.generation_jobs.c.product_id.in_(product_ids), limit=20)
    settings = runtime_settings(conn, request.app.state.settings)
    trend = []
    for i in range(14):
        day = (start + timedelta(days=i)).isoformat()
        # 跨日记录只计入汇总；趋势仅展示日粒度记录，避免把多日金额重复铺开。
        daily = [r for r in recent if r['period_start'] == day and r['period_end'] == day]
        trend.append({'date': day, **metrics(daily)})
    return {'summary': {'store_count': len(stores), 'product_count': len(products),
        'low_stock_count': sum(sku['low_stock'] for sku in skus),
        'pending_jobs': sum(j['job_status'] in {'pending', 'running'} for j in rows(conn, m.generation_jobs,
            m.generation_jobs.c.product_id.in_(product_ids))), **metrics(recent)},
        'stores': stores, 'products': products, 'low_stock': [sku for sku in skus if sku['low_stock']],
        'jobs': jobs, 'trend': trend, 'period_start': start.isoformat(), 'period_end': today.isoformat(),
        'mode': settings.ai_mode, 'has_demo_data': bool(rows(conn, m.system_settings, m.system_settings.c.key == 'demo_seed'))}


@router.post('/demo-data')
def demo(request: Request, actor=Depends(admin), conn=Depends(get_conn)):
    if not request.app.state.settings.demo_enabled:
        raise HTTPException(403, '当前环境已关闭演示数据入口')
    return seed_demo(conn, request.app.state.settings, actor)


@router.get('/templates/{kind}')
def template(kind: str):
    return Response(template_csv(kind).encode('utf-8'), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{kind}.csv"'})


@router.post('/imports/{kind}/preview')
def preview(kind: str, data: s.ImportRows, actor=Depends(writer), conn=Depends(get_conn)):
    return import_rows(conn, kind, data.rows, preview=True)


@router.post('/imports/{kind}/preview-file')
async def preview_file(kind: str, file: UploadFile = File(...), actor=Depends(writer), conn=Depends(get_conn)):
    content = await file.read(5 * 1024 * 1024 + 1)
    return import_rows(conn, kind, parse_csv(content), preview=True)


@router.post('/imports/{kind}')
def commit_import(kind: str, data: s.ImportRows, actor=Depends(writer), conn=Depends(get_conn)):
    return import_rows(conn, kind, data.rows)


@router.post('/generation-jobs/sweep-timeouts')
def sweep(request: Request, actor=Depends(admin), conn=Depends(get_conn)):
    return {'timeout_count': sweep_timeouts(conn, request.app.state.settings)}


@router.post('/competitor-monitors/run-due')
def due_monitors(request: Request, actor=Depends(writer)):
    return run_due(request.app.state.db)


@router.get('/settings')
def settings(request: Request, actor=Depends(admin), conn=Depends(get_conn)):
    config = runtime_settings(conn, request.app.state.settings)
    return {'ai_mode': config.ai_mode, 'ai_text_model': config.ai_text_model,
        'ai_image_model': config.ai_image_model, 'ai_base_url': config.ai_base_url,
        'text_model_configured': bool(config.ai_api_key and config.ai_text_model),
        'image_model_configured': bool(config.ai_api_key and config.ai_image_model),
        'video_model_configured': bool(config.video_api_url and config.video_api_key),
        'job_timeout_seconds': config.job_timeout_seconds, 'job_max_attempts': config.job_max_attempts,
        'worker_enabled': config.worker_enabled, 'demo_enabled': config.demo_enabled,
        'note': '密钥通过后端环境变量配置，不通过网页回传；视频服务遵循 README 中的适配协议。'}


@router.patch('/settings')
def patch_settings(data: s.SettingsPatch, request: Request, actor=Depends(admin), conn=Depends(get_conn)):
    old = runtime_settings(conn, request.app.state.settings)
    values = data.model_dump(exclude_unset=True)
    if values.get('ai_mode') == 'compatible' and not (old.ai_api_key and old.ai_text_model):
        raise HTTPException(422, '请先在后端环境变量配置文本模型与密钥，再切换真实模型模式')
    records = rows(conn, m.system_settings, m.system_settings.c.key == 'runtime')
    merged = {**(records[0]['value_json'] if records else {}), **values}
    if records:
        update(conn, m.system_settings, records[0]['id'], {'value_json': merged})
    else:
        insert(conn, m.system_settings, {'key': 'runtime', 'value_json': merged})
    return settings(request, actor, conn)

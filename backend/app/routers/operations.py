import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from .. import models as m, schemas as s
from ..db import get_conn, insert, one, rows, update
from ..security import current_user, writer, confirm_ads, manage_experiments
from ..services.ai import generate
from ..services.catalog import save_performance
from ..services.jobs import enqueue, change_job
from ..services.imports import import_rows

router = APIRouter(prefix='/api/v1/products/{product_id}', tags=['单品运营'], dependencies=[Depends(current_user)])
public_router = APIRouter(prefix='/api/v1', tags=['推广追踪'])


@router.post('/diagnoses/generate')
def diagnose(product_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    content, source = generate(conn, request.app.state.settings, product_id, 'diagnosis')
    return insert(conn, m.product_diagnoses, {'product_id': product_id, 'source_type': source, **content})


@router.patch('/diagnoses/{diagnosis_id}')
def edit_diagnosis(product_id: int, diagnosis_id: int, data: s.DiagnosisPatch, actor=Depends(writer), conn=Depends(get_conn)):
    return update(conn, m.product_diagnoses, diagnosis_id, data.model_dump(exclude_unset=True), product_id)


def create_plans(conn, request, product_id, kind):
    one(conn, m.products, product_id)
    if not rows(conn, m.product_diagnoses, m.product_diagnoses.c.product_id == product_id):
        raise HTTPException(409, '请先生成商品诊断，再生成方案')
    result, source = generate(conn, request.app.state.settings, product_id, kind)
    return [insert(conn, m.creative_plans, {'product_id': product_id, 'plan_type': kind,
        **plan}) for plan in result['plans']]


@router.post('/creative-plans/main-images/generate')
def main_images(product_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    return create_plans(conn, request, product_id, 'main_image')


@router.post('/creative-plans/video-scripts/generate')
def video_scripts(product_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    return create_plans(conn, request, product_id, 'video_script')


@router.patch('/creative-plans/{creative_plan_id}')
def edit_plan(product_id: int, creative_plan_id: int, data: s.PlanPatch, actor=Depends(writer), conn=Depends(get_conn)):
    plan = one(conn, m.creative_plans, creative_plan_id, product_id)
    values = data.model_dump(exclude_unset=True)
    if 'content_json' in values:
        schema = s.ImageContent if plan['plan_type'] == 'main_image' else s.VideoContent
        try:
            values['content_json'] = schema.model_validate(values['content_json']).model_dump()
        except ValueError:
            raise HTTPException(422, '方案内容结构不完整，请保留该类型的所有内容字段')
    return update(conn, m.creative_plans, creative_plan_id, values)


@router.post('/creative-plans/{creative_plan_id}/images/generate', status_code=202)
def generate_image(product_id: int, creative_plan_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    return enqueue(conn, request.app.state.settings, product_id, creative_plan_id, 'image')


@router.post('/creative-plans/{creative_plan_id}/videos/generate', status_code=202)
def generate_video(product_id: int, creative_plan_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    return enqueue(conn, request.app.state.settings, product_id, creative_plan_id, 'video')


@router.post('/generation-jobs/{job_id}/retry')
def retry(product_id: int, job_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    return change_job(conn, product_id, job_id, 'retry')


@router.post('/generation-jobs/{job_id}/cancel')
def cancel(product_id: int, job_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    return change_job(conn, product_id, job_id, 'cancel')


@router.get('/generation-jobs')
def jobs(product_id: int, conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    result = rows(conn, m.generation_jobs, m.generation_jobs.c.product_id == product_id)
    for job in result:
        job['events'] = list(reversed(rows(conn, m.generation_job_events, m.generation_job_events.c.job_id == job['id'])))
    return result


@router.post('/assets/sync')
def sync_assets(product_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    assets = rows(conn, m.generated_assets, m.generated_assets.c.product_id == product_id)
    return {'assets': assets, 'synced_count': len(assets), 'message': '生成任务的输出已自动入库，素材列表已刷新'}


@router.patch('/assets/{asset_id}')
def edit_asset(product_id: int, asset_id: int, data: s.AssetPatch, actor=Depends(writer), conn=Depends(get_conn)):
    return update(conn, m.generated_assets, asset_id, data.model_dump(exclude_unset=True), product_id)


@router.patch('/creative-plans/{creative_plan_id}/assets')
def edit_plan_asset(product_id: int, creative_plan_id: int, data: s.PlanAssetsPatch, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.creative_plans, creative_plan_id, product_id)
    asset = one(conn, m.generated_assets, data.asset_id, product_id)
    if asset['creative_plan_id'] != creative_plan_id:
        raise HTTPException(404, '素材不属于此方案')
    return update(conn, m.generated_assets, data.asset_id, data.model_dump(exclude_unset=True, exclude={'asset_id'}))


@router.post('/promotion-links/generate')
def suggest_links(product_id: int, actor=Depends(writer), conn=Depends(get_conn)):
    product = one(conn, m.products, product_id)
    return {'suggestions': [{'link_name': product['name'] + ' · ' + scene,
        'target_url': product['product_url'], 'scene_text': scene,
        'utm_json': {'utm_source': product['platform'], 'utm_medium': medium, 'utm_campaign': f'product_{product_id}'}}
        for scene, medium in [('主图测试', 'image'), ('视频内容', 'video'), ('店铺推荐', 'store')]],
        'note': '目标链接需由运营核对；追踪数据只统计经过本系统跳转的点击。'}


@router.post('/promotion-links', status_code=201)
def create_link(product_id: int, data: s.PromotionCreate, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    return insert(conn, m.promotion_links, {'product_id': product_id, 'tracking_code': secrets.token_urlsafe(12), **data.model_dump()})


@public_router.get('/r/{tracking_code}')
def redirect(tracking_code: str, request: Request, conn=Depends(get_conn)):
    matches = rows(conn, m.promotion_links, m.promotion_links.c.tracking_code == tracking_code, m.promotion_links.c.status == 'active')
    if not matches:
        raise HTTPException(404, '推广链接不存在或已停用')
    link = matches[0]
    s.http_url(link['target_url'])
    insert(conn, m.promotion_link_clicks, {'promotion_link_id': link['id'], 'clicked_at': m.utcnow(),
        'client_ip': request.client.host if request.client else '', 'user_agent': request.headers.get('user-agent', '')[:500]})
    conn.execute(m.promotion_links.update().where(m.promotion_links.c.id == link['id']).values(click_count=m.promotion_links.c.click_count + 1))
    parts = urlsplit(link['target_url'])
    params = dict(parse_qsl(parts.query))
    params.update(link['utm_json'])
    return RedirectResponse(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment)), status_code=302)


@router.post('/ad-recommendations/generate')
def recommend(product_id: int, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    if not rows(conn, m.generated_assets, m.generated_assets.c.product_id == product_id, m.generated_assets.c.review_status == 'approved'):
        raise HTTPException(409, '请先生成素材，并至少审核通过一份素材')
    content, source = generate(conn, request.app.state.settings, product_id, 'ad')
    return insert(conn, m.ad_recommendations, {'product_id': product_id, 'source_type': source, **content})


@router.patch('/ad-recommendations/{recommendation_id}')
def edit_recommendation(product_id: int, recommendation_id: int, data: s.AdPatch, actor=Depends(writer), conn=Depends(get_conn)):
    rec = one(conn, m.ad_recommendations, recommendation_id, product_id)
    if rec['confirm_status'] != 'pending':
        raise HTTPException(409, '已确认或驳回的建议不能修改，请生成下一版')
    return update(conn, m.ad_recommendations, recommendation_id, data.model_dump(exclude_unset=True))


@router.patch('/ad-recommendations/{recommendation_id}/confirmation')
def confirm(product_id: int, recommendation_id: int, data: s.Confirmation, actor=Depends(confirm_ads), conn=Depends(get_conn)):
    rec = one(conn, m.ad_recommendations, recommendation_id, product_id)
    if rec['confirm_status'] != 'pending':
        raise HTTPException(409, '该建议已处理，不能重复确认')
    if data.confirm_status == 'confirmed' and not rows(conn, m.generated_assets,
            m.generated_assets.c.product_id == product_id, m.generated_assets.c.review_status == 'approved'):
        raise HTTPException(409, '当前没有审核通过的素材，不能确认投放建议')
    return update(conn, m.ad_recommendations, recommendation_id, {**data.model_dump(), 'confirmed_by': actor['id'], 'confirmed_at': m.utcnow()})


@router.post('/ad-experiments/generate')
def experiment(product_id: int, data: s.ExperimentCreate, actor=Depends(manage_experiments), conn=Depends(get_conn)):
    rec = one(conn, m.ad_recommendations, data.recommendation_id, product_id)
    if rec['confirm_status'] != 'confirmed':
        raise HTTPException(409, '请先人工确认投放建议')
    approved = rows(conn, m.generated_assets, m.generated_assets.c.product_id == product_id, m.generated_assets.c.review_status == 'approved')
    asset = one(conn, m.generated_assets, data.related_asset_id, product_id) if data.related_asset_id else (approved[0] if approved else None)
    if not asset or asset['review_status'] != 'approved':
        raise HTTPException(409, '实验必须关联审核通过的素材')
    if data.related_link_id:
        one(conn, m.promotion_links, data.related_link_id, product_id)
    raw_budget = rec['budget_plan_json'].get('total_budget', 0)
    try:
        budget = max(0, min(float(raw_budget), 100000000))
    except (ValueError, TypeError):
        budget = 0
    return insert(conn, m.ad_experiments, {'product_id': product_id, 'recommendation_id': rec['id'],
        'related_asset_id': asset['id'], 'related_link_id': data.related_link_id,
        'experiment_name': '素材对比测试 · 建议 #' + str(rec['id']), 'target_text': rec['objective_text'],
        'audience_text': '；'.join(rec['audience_segments_json']), 'budget_amount': budget,
        'success_metric_text': '比较点击率、转化率与收入/花费，核对数据口径',
        'hypothesis_text': '清晰的商品卖点可能改善用户理解，需要实际数据验证'})


@router.patch('/ad-experiments/{experiment_id}')
def edit_experiment(product_id: int, experiment_id: int, data: s.ExperimentPatch, actor=Depends(manage_experiments), conn=Depends(get_conn)):
    exp = one(conn, m.ad_experiments, experiment_id, product_id)
    values = data.model_dump(exclude_unset=True)
    target_status = values.get('experiment_status', exp['experiment_status'])
    transitions = {'draft': {'confirmed', 'cancelled'}, 'confirmed': {'running', 'cancelled'},
                   'running': {'finished', 'cancelled'}, 'finished': set(), 'cancelled': set()}
    if target_status != exp['experiment_status'] and target_status not in transitions[exp['experiment_status']]:
        raise HTTPException(409, '实验状态流转无效，请依次执行：草稿 → 确认 → 运行 → 完成')
    if exp['experiment_status'] != 'draft' and set(values) - {'experiment_status'}:
        raise HTTPException(409, '实验确认后不能修改预算和实验条件，请新建实验')
    if target_status == 'running':
        asset = one(conn, m.generated_assets, exp['related_asset_id'], product_id)
        if asset['review_status'] != 'approved':
            raise HTTPException(409, '关联素材已不再审核通过，请先处理素材')
    return update(conn, m.ad_experiments, experiment_id, values)


@router.post('/performance-records', status_code=201)
def performance(product_id: int, data: s.PerformanceCreate, actor=Depends(writer), conn=Depends(get_conn)):
    return save_performance(conn, product_id, data)


@router.post('/performance-records/import')
def import_performance(product_id: int, data: s.ImportRows, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    if any('product_id' in row and str(row['product_id']) != str(product_id) for row in data.rows):
        raise HTTPException(422, '导入行包含其他商品的 product_id')
    return import_rows(conn, 'performance-records', [{**row, 'product_id': product_id} for row in data.rows])


@router.post('/review-reports/generate')
def review(product_id: int, data: s.Period, request: Request, actor=Depends(writer), conn=Depends(get_conn)):
    one(conn, m.products, product_id)
    records = rows(conn, m.performance_records, m.performance_records.c.product_id == product_id,
        m.performance_records.c.period_start >= data.period_start.isoformat(),
        m.performance_records.c.period_end <= data.period_end.isoformat())
    if not records:
        raise HTTPException(409, '所选周期没有完整落在区间内的经营记录，请先录入或调整日期')
    content, source = generate(conn, request.app.state.settings, product_id, 'review', records)
    return insert(conn, m.review_reports, {'product_id': product_id, 'source_type': source,
        **data.model_dump(mode='json'), **content})


@router.patch('/review-reports/{report_id}')
def edit_review(product_id: int, report_id: int, data: s.ReviewPatch, actor=Depends(writer), conn=Depends(get_conn)):
    return update(conn, m.review_reports, report_id, data.model_dump(exclude_unset=True), product_id)

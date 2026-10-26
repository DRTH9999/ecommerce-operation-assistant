from datetime import UTC, datetime, timedelta
import logging
import threading
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from .. import models as m
from ..db import insert, one, rows
from .ai import runtime_settings
from .media import generate_media

logger = logging.getLogger(__name__)


def event(conn, job_id, kind, message):
    return insert(conn, m.generation_job_events, {'job_id': job_id, 'event_type': kind, 'event_message': message})


def enqueue(conn, settings, product_id, plan_id, kind):
    plan = one(conn, m.creative_plans, plan_id, product_id)
    if plan['status'] == 'archived':
        raise HTTPException(409, '已归档方案不能生成素材')
    expected = 'main_image' if kind == 'image' else 'video_script'
    if plan['plan_type'] != expected:
        raise HTTPException(422, '方案类型与生成任务不匹配')
    pending = rows(conn, m.generation_jobs, m.generation_jobs.c.creative_plan_id == plan_id,
                   m.generation_jobs.c.job_status.in_(['pending', 'running']))
    if pending:
        raise HTTPException(409, '该方案已有待处理任务，请先等待完成或取消')
    settings = runtime_settings(conn, settings)
    job = insert(conn, m.generation_jobs, {'product_id': product_id, 'creative_plan_id': plan_id,
        'job_kind': kind, 'max_attempts': settings.job_max_attempts, 'next_run_at': m.utcnow()})
    event(conn, job['id'], 'queued', '生成任务已入队，等待执行')
    return job


def change_job(conn, product_id, job_id, action):
    job = one(conn, m.generation_jobs, job_id, product_id)
    if action == 'retry':
        if job['job_status'] not in {'failed', 'timeout'}:
            raise HTTPException(409, '只能重试失败或超时的任务')
        if job['attempts'] >= job['max_attempts']:
            raise HTTPException(409, '已达到最大尝试次数，请新建任务')
        values = {'job_status': 'pending', 'error_message': '', 'locked_by': '', 'locked_at': None,
                  'next_run_at': m.utcnow(), 'finished_at': None, 'started_at': None}
        message = '已申请重试，任务重新入队'
    else:
        if job['job_status'] not in {'pending', 'running'}:
            raise HTTPException(409, '只有等待中或运行中的任务可以取消')
        values = {'job_status': 'cancelled', 'finished_at': m.utcnow(), 'locked_by': ''}
        message = '任务已取消，后续返回结果不会写入素材库'
    changed = conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == job_id,
        m.generation_jobs.c.job_status == job['job_status'], m.generation_jobs.c.locked_by == job['locked_by']).values(**values))
    if changed.rowcount != 1:
        raise HTTPException(409, '任务状态已变化，请刷新')
    event(conn, job_id, 'retry' if action == 'retry' else 'cancelled', message)
    return one(conn, m.generation_jobs, job_id)


def sweep_timeouts(conn, settings):
    settings = runtime_settings(conn, settings)
    cutoff = (datetime.now(UTC) - timedelta(seconds=settings.job_timeout_seconds)).isoformat(timespec='milliseconds')
    due = rows(conn, m.generation_jobs, m.generation_jobs.c.job_status == 'running',
               m.generation_jobs.c.locked_at < cutoff)
    count = 0
    for job in due:
        result = conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == job['id'],
            m.generation_jobs.c.job_status == 'running', m.generation_jobs.c.locked_by == job['locked_by']).values(
                job_status='timeout', finished_at=m.utcnow(), error_message='任务超过执行时限', locked_by=''))
        if result.rowcount:
            event(conn, job['id'], 'timeout', '任务超过执行时限，可在次数限制内手动重试')
            count += 1
    return count


class JobWorker:
    def __init__(self, database, settings):
        self.database, self.settings = database, settings
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name='generation-worker', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)

    def run(self):
        while not self.stop_event.wait(1):
            try:
                with self.database.transaction() as conn:
                    sweep_timeouts(conn, self.settings)
                self.run_once()
            except Exception:
                logger.exception('Worker iteration failed')

    def claim(self):
        with self.database.transaction() as conn:
            candidate = conn.execute(select(m.generation_jobs).where(
                m.generation_jobs.c.job_status == 'pending', m.generation_jobs.c.next_run_at <= m.utcnow(),
                m.generation_jobs.c.attempts < m.generation_jobs.c.max_attempts).order_by(m.generation_jobs.c.id).limit(1)).mappings().first()
            if not candidate:
                return None
            lease = uuid.uuid4().hex
            result = conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == candidate['id'],
                m.generation_jobs.c.job_status == 'pending', m.generation_jobs.c.attempts == candidate['attempts']).values(
                    job_status='running', attempts=candidate['attempts'] + 1, locked_by=lease,
                    locked_at=m.utcnow(), started_at=m.utcnow()))
            if result.rowcount != 1:
                return None
            event(conn, candidate['id'], 'running', f'开始第 {candidate["attempts"] + 1} 次生成')
            return one(conn, m.generation_jobs, candidate['id'])

    def run_once(self):
        job = self.claim()
        if not job:
            return False
        try:
            with self.database.transaction() as conn:
                product = one(conn, m.products, job['product_id'])
                plan = one(conn, m.creative_plans, job['creative_plan_id'])
                settings = runtime_settings(conn, self.settings)
            result = generate_media(settings, product, plan, job)
            with self.database.transaction() as conn:
                # 租约检查：取消、超时或旧尝试迟到时，不允许把结果写成成功。
                current = one(conn, m.generation_jobs, job['id'])
                if current['job_status'] != 'running' or current['locked_by'] != job['locked_by']:
                    self.discard(result)
                    return True
                elapsed = datetime.now(UTC) - datetime.fromisoformat(job['locked_at'])
                if elapsed.total_seconds() > settings.job_timeout_seconds:
                    conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == job['id']).values(
                        job_status='timeout', finished_at=m.utcnow(), locked_by='', error_message='任务超过执行时限'))
                    event(conn, job['id'], 'timeout', '生成已超时，丢弃过期输出')
                    self.discard(result)
                    return True
                version = 1 + len(rows(conn, m.generated_assets, m.generated_assets.c.creative_plan_id == plan['id']))
                asset = insert(conn, m.generated_assets, {'product_id': job['product_id'], 'creative_plan_id': plan['id'],
                    'job_id': job['id'], 'asset_type': job['job_kind'], 'version_no': version,
                    'usage_scene': '主图' if job['job_kind'] == 'image' else '短视频',
                    'remark': '演示排版/动态分镜，非真实商品拍摄，须替换商品图后审核' if settings.ai_mode == 'demo' else '模型生成，使用前请人工核实', **result})
                conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == job['id']).values(
                    job_status='succeeded', result_json={'asset_id': asset['id'], **result}, finished_at=m.utcnow(), locked_by=''))
                event(conn, job['id'], 'succeeded', '生成完成，素材已入库，等待人工审核')
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else '素材服务执行失败，请检查模型配置或稍后重试'
            with self.database.transaction() as conn:
                result = conn.execute(m.generation_jobs.update().where(m.generation_jobs.c.id == job['id'],
                    m.generation_jobs.c.job_status == 'running', m.generation_jobs.c.locked_by == job['locked_by']).values(
                        job_status='failed', finished_at=m.utcnow(), error_message=message[:500], locked_by=''))
                if result.rowcount:
                    event(conn, job['id'], 'failed', message[:500])
        return True

    def discard(self, result):
        filename = result.get('asset_url', '').removeprefix('/media/')
        path = self.settings.data_dir / 'media' / filename
        if path.is_file() and path.parent.resolve() == (self.settings.data_dir / 'media').resolve():
            path.unlink()

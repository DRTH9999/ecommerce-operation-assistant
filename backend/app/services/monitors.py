from datetime import UTC, datetime, timedelta
import logging
import threading

from fastapi import HTTPException

from .. import models as m
from ..db import insert, one, rows
from .public_links import parse_public_page

logger = logging.getLogger(__name__)


def run_due(database, limit=20):
    with database.transaction() as conn:
        due = rows(conn, m.competitor_monitors, m.competitor_monitors.c.monitor_status == 'active',
                   m.competitor_monitors.c.next_run_at <= m.utcnow(), limit=limit)
    results = []
    for monitor in due:
        with database.transaction() as conn:
            # 提前推进下次执行时间作为领取标记，避免手动运行与定时线程重复抓取。
            next_run = (datetime.now(UTC) + timedelta(minutes=monitor['interval_minutes'])).isoformat(timespec='milliseconds')
            claimed = conn.execute(m.competitor_monitors.update().where(m.competitor_monitors.c.id == monitor['id'],
                m.competitor_monitors.c.monitor_status == 'active',
                m.competitor_monitors.c.next_run_at == monitor['next_run_at']).values(next_run_at=next_run))
            if claimed.rowcount != 1:
                continue
            competitor = one(conn, m.competitors, monitor['competitor_id'])
        # 公网页面读取期间不持有数据库写事务。
        try:
            payload = parse_public_page(competitor['url'])
            payload.update(parse_status='succeeded', price_observed=payload.get('price', 0) > 0)
        except HTTPException as exc:
            payload = {'parse_status': 'failed', 'error_message': str(exc.detail), 'price_observed': False}
        with database.transaction() as conn:
            snapshot = insert(conn, m.competitor_monitor_snapshots, {'monitor_id': monitor['id'],
                'price': payload.get('price', 0), 'selling_points': payload.get('selling_points', ''), 'raw_payload_json': payload})
        results.append(snapshot)
    return {'run_count': len(results), 'snapshots': results,
            'message': '公开元信息已记录；无法读取时保存失败快照，不绕过平台限制'}


class MonitorScheduler:
    def __init__(self, database):
        self.database = database
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name='competitor-scheduler', daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop_event.wait(30):
            try:
                run_due(self.database, limit=5)
            except Exception:
                logger.exception('Competitor scheduler iteration failed')

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

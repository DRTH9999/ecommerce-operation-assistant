"""独立队列执行器。Web 服务设置 WORKER_ENABLED=false 后，在另一个终端运行。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.db import Database
from app.main import initialize
from app.services.jobs import JobWorker
from app.services.monitors import MonitorScheduler

settings = get_settings()
database = Database(settings)
initialize(database, settings)
worker = JobWorker(database, settings)
monitors = MonitorScheduler(database)
try:
    monitors.start()
    print('队列执行器已启动，按 Ctrl+C 停止。')
    worker.run()
except KeyboardInterrupt:
    pass
finally:
    worker.stop()
    monitors.stop()
    database.engine.dispose()

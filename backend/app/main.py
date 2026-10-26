from contextlib import asynccontextmanager
from pathlib import Path
import secrets

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from . import models as m
from .config import BACKEND_DIR, Settings, get_settings
from .db import Database, insert, rows
from .routers import auth, catalog, operations, workspace
from .security import LoginLimiter, hash_password
from .services.jobs import JobWorker
from .services.monitors import MonitorScheduler
from .validation import validation_message


def initialize(database, settings):
    database.initialize()
    key_file = settings.data_dir / '.signing-key'
    if settings.jwt_secret:
        signing_key = settings.jwt_secret
    else:
        if not key_file.exists():
            try:
                with key_file.open('x', encoding='utf-8') as file:
                    file.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
        signing_key = key_file.read_text(encoding='utf-8').strip()
    with database.transaction() as conn:
        if not rows(conn, m.users):
            password = settings.bootstrap_admin_password or ('Admin@123456' if settings.demo_enabled else secrets.token_urlsafe(18))
            insert(conn, m.users, {'username': settings.bootstrap_admin_username, 'display_name': '管理员',
                'role': 'admin', 'password_hash': hash_password(password)})
            if not settings.bootstrap_admin_password and not settings.demo_enabled:
                (settings.data_dir / 'initial-admin-password.txt').write_text(password, encoding='utf-8')
    return signing_key


def create_app(config: Settings | None = None):
    config = config or get_settings()
    database = Database(config)

    @asynccontextmanager
    async def lifespan(application):
        application.state.signing_key = initialize(database, config)
        (config.data_dir / 'media').mkdir(parents=True, exist_ok=True)
        worker = JobWorker(database, config)
        application.state.worker = worker
        monitors = MonitorScheduler(database)
        application.state.monitors = monitors
        if config.worker_enabled:
            worker.start()
            monitors.start()
        yield
        monitors.stop()
        worker.stop()
        database.engine.dispose()

    app = FastAPI(title=config.app_name, version='1.0.0', lifespan=lifespan,
        description='商品建档 → 竞品 → 诊断 → 创意 → 素材审核 → 投放建议确认 → 经营数据 → 复盘。默认演示模式。')
    app.state.db, app.state.settings = database, config
    app.state.login_limiter = LoginLimiter()
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173'],
        allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Authorization', 'Content-Type'])

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(status_code=409, content={'detail': '记录已存在，或关联数据不满足约束，请刷新后重试'})

    @app.exception_handler(RequestValidationError)
    async def input_error(request, exc):
        return JSONResponse(status_code=422, content={'detail': [
            {'loc': list(error['loc']), 'type': error['type'], 'msg': validation_message(error)}
            for error in exc.errors()]})

    @app.get('/api/health', tags=['运行状态'])
    def health():
        return {'status': 'ok', 'app': config.app_name, 'demo_enabled': config.demo_enabled}

    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(operations.router)
    app.include_router(operations.public_router)
    app.include_router(workspace.router)
    media = config.data_dir / 'media'
    media.mkdir(parents=True, exist_ok=True)
    app.mount('/media', StaticFiles(directory=media), name='media')
    frontend = BACKEND_DIR.parent / 'frontend' / 'dist'
    if frontend.exists():
        app.mount('/assets', StaticFiles(directory=frontend / 'assets', check_dir=False), name='frontend-assets')

        @app.get('/{path:path}', include_in_schema=False)
        def spa(path: str):
            if path.startswith(('api/', 'media/')):
                return JSONResponse(status_code=404, content={'detail': '接口不存在'})
            return FileResponse(frontend / 'index.html')
    return app


app = create_app()

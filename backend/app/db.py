from contextlib import contextmanager

from fastapi import HTTPException, Request
from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

from . import models as m
from .config import Settings


class Database:
    def __init__(self, settings: Settings):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        options = {}
        if settings.db_url.startswith('sqlite'):
            options['connect_args'] = {'check_same_thread': False, 'timeout': 20}
            if ':memory:' in settings.db_url:
                options['poolclass'] = StaticPool
        self.engine = create_engine(settings.db_url, **options)
        if settings.db_url.startswith('sqlite'):
            @event.listens_for(self.engine, 'connect')
            def configure_sqlite(dbapi_connection, _):
                cursor = dbapi_connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.close()

    def initialize(self):
        m.metadata.create_all(self.engine)

    @contextmanager
    def transaction(self):
        with self.engine.begin() as connection:
            yield connection


def get_conn(request: Request):
    with request.app.state.db.transaction() as connection:
        yield connection


def rows(conn, table, *conditions, limit=1000):
    query = select(table).where(*conditions).order_by(table.c.id.desc()).limit(limit)
    return [dict(row) for row in conn.execute(query).mappings()]


def one(conn, table, entity_id, product_id=None):
    conditions = [table.c.id == entity_id]
    if product_id is not None:
        conditions.append(table.c.product_id == product_id)
    result = conn.execute(select(table).where(*conditions)).mappings().first()
    if not result:
        raise HTTPException(404, '记录不存在或不属于当前商品')
    return dict(result)


def insert(conn, table, values):
    result = conn.execute(table.insert().values(**values))
    return one(conn, table, result.inserted_primary_key[0])


def update(conn, table, entity_id, values, product_id=None):
    one(conn, table, entity_id, product_id)
    if values:
        conn.execute(table.update().where(table.c.id == entity_id).values(**values))
    return one(conn, table, entity_id)

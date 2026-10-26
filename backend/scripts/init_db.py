"""从 backend 目录执行：python scripts/init_db.py [--demo] [--export-sql]。"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.dialects import sqlite
from app import models as m
from app.config import get_settings
from app.db import Database, rows
from app.main import initialize
from app.services.demo import seed_demo

parser = argparse.ArgumentParser()
parser.add_argument('--demo', action='store_true')
parser.add_argument('--export-sql', action='store_true')
args = parser.parse_args()
config = get_settings()
db = Database(config)
initialize(db, config)
if args.demo:
    if not config.demo_enabled:
        raise SystemExit('DEMO_ENABLED=false，禁止初始化演示数据')
    with db.transaction() as conn:
        actor = rows(conn, m.users, m.users.c.role == 'admin')[0]
        print(seed_demo(conn, config, actor)['message'])
if args.export_sql:
    parts = ['-- 由 SQLAlchemy 模型生成；账户和演示数据请运行初始化脚本。', 'PRAGMA foreign_keys=ON;']
    for table in m.metadata.sorted_tables:
        parts.append(str(CreateTable(table).compile(dialect=sqlite.dialect())) + ';')
        parts.extend(str(CreateIndex(index).compile(dialect=sqlite.dialect())) + ';' for index in table.indexes)
    target = Path(__file__).resolve().parents[1] / 'schema.sql'
    target.write_text('\n\n'.join(parts), encoding='utf-8')
    print('已导出 schema.sql')
print('数据库初始化完成。')

"""
迁移脚本：聚合 worker 新增字段 + 表
- tasks.model_version / tasks.aggregation_key（ALTER，不破坏现有数据）
- aggregation_records 表（create_all 若缺失）
"""
import asyncio
from sqlalchemy import text
from app.database import engine, Base
# 触发模型注册到 Base.metadata
from app.models import task, node, user, contribution  # noqa
from app.models.aggregation import AggregationRecord  # noqa


async def migrate():
    async with engine.begin() as conn:
        # 1) tasks 新字段（IF NOT EXISTS 幂等）
        await conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS model_version VARCHAR(64) DEFAULT 'v0.1'"))
        await conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS aggregation_key VARCHAR(128)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_tasks_aggregation "
            "ON tasks(model_version, aggregation_key)"))
        # 2) aggregation_records 表（仅建缺失表）
        await conn.run_sync(lambda sync: Base.metadata.create_all(sync, checkfirst=True))
        # 3) 既有任务补默认值，便于聚合
        await conn.execute(text(
            "UPDATE tasks SET model_version='v0.1' WHERE model_version IS NULL"))
        await conn.execute(text(
            "UPDATE tasks SET aggregation_key='default' WHERE aggregation_key IS NULL"))
    print("MIGRATION OK")


asyncio.run(migrate())

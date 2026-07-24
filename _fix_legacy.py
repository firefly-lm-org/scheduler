"""把新 E2E 任务之外的 completed 老任务隔离到 legacy 分组"""
import asyncio
from sqlalchemy import text
from app.database import engine

NEW_IDS = (
    "ada37ef9-6bbe-43ee-8813-087c8cba7cf9",
    "8fe30910-a323-46ea-b4d1-0761c6c41fcb",
    "18e6bdc3-ef3f-4bce-8f95-979fec123be9",
)

async def main():
    async with engine.begin() as conn:
        r = await conn.execute(text(
            "UPDATE tasks SET aggregation_key='legacy' "
            "WHERE status='completed' AND NOT (id = ANY(:ids))"
        ), {"ids": list(NEW_IDS)})
        print("moved to legacy:", r.rowcount)
        rows = await conn.execute(text(
            "SELECT id, status, model_version, aggregation_key, result_object_name "
            "FROM tasks WHERE status='completed'"))
        for row in rows:
            print(row)

asyncio.run(main())

import asyncio
from app.database import engine

async def main():
    async with engine.connect() as conn:
        # aggregation_records 表是否存在
        r = await conn.execute(__import__("sqlalchemy").text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='aggregation_records'"))
        rows = r.fetchall()
        print("aggregation_records:", rows if rows else "TABLE_MISSING")
        # tasks 新字段
        r2 = await conn.execute(__import__("sqlalchemy").text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='tasks' "
            "AND column_name IN ('model_version','aggregation_key')"))
        print("tasks new cols:", r2.fetchall())

asyncio.run(main())

import asyncio, asyncpg, sys

async def test():
    try:
        conn = await asyncpg.connect('postgresql://firefly:firefly123@localhost:5432/firefly', timeout=5)
        r = await conn.fetchval('SELECT 1')
        print('PG async OK:', r, flush=True)
        await conn.close()
    except Exception as e:
        print('ERROR:', type(e).__name__, str(e), flush=True)

asyncio.run(test())
print('DONE', flush=True)

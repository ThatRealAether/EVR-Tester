import asyncio
import asyncpg
import os

async def drop_table():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DROP TABLE team_members;")
    print("Table dropped")
    await conn.close()

asyncio.run(drop_table())

import json
import asyncpg
import asyncio
import os

async def migrate_stats():
    DATABASE_URL = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(DATABASE_URL)

    with open('stats.json', 'r') as f:
        user_stats = json.load(f)

    for user_id, data in user_stats.items():
        wins = data.get('wins', 0)
        br = data.get('br', [])
        events = data.get('events', [])

        await conn.execute('''
            INSERT INTO stats (user_id, wins, br_placements, events)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE
            SET wins = EXCLUDED.wins,
                br_placements = EXCLUDED.br_placements,
                events = EXCLUDED.events
        ''', user_id, wins, br, events)

    await conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    asyncio.run(migrate_stats())

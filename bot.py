import os
import logging
import discord
from discord.ext import commands
import asyncpg

class EventCog(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    async def init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    user_id TEXT PRIMARY KEY,
                    wins INTEGER DEFAULT 0,
                    br_placements TEXT[] DEFAULT '{}',
                    events TEXT[] DEFAULT '{}'
                )
            """)

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def eventreg(self, ctx, player: discord.Member, event_name: str, is_battle_royal: str, placement_or_date: str = None, date: str = None):
        is_br = is_battle_royal.lower() in ("true", "yes", "1", "y")
        uid = str(player.id)

        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT * FROM stats WHERE user_id = $1", uid)
            if not record:
                # Insert new record
                await conn.execute("INSERT INTO stats (user_id) VALUES ($1)", uid)
                record = await conn.fetchrow("SELECT * FROM stats WHERE user_id = $1", uid)

            wins = record['wins']
            br_placements = record['br_placements'] or []
            events = record['events'] or []

            if is_br:
                if placement_or_date is None or date is None:
                    await ctx.send("You must specify placement and date for a battle royal event. Example:\n`!eventreg @player event_name true 1st 7/25`")
                    return
                placement = placement_or_date
                br_placements.append(placement)
                events.append(f"{event_name} (Date: {date})")
                if placement.lower().startswith("1"):
                    wins += 1
                await conn.execute("""
                    UPDATE stats SET wins=$1, br_placements=$2, events=$3 WHERE user_id=$4
                """, wins, br_placements, events, uid)
                await ctx.send(f"Recorded battle royal event **{event_name}** for {player.display_name} with placement {placement} on {date}.")
            else:
                date = placement_or_date
                if date is None:
                    await ctx.send("You must specify the date for a non-battle royal event. Example:\n`!eventreg @player event_name false 7/25`")
                    return
                events.append(f"{event_name} (Date: {date})")
                wins += 1
                await conn.execute("""
                    UPDATE stats SET wins=$1, events=$2 WHERE user_id=$3
                """, wins, events, uid)
                await ctx.send(f"Recorded non-battle royal event **{event_name}** for {player.display_name} on {date}.")

    @commands.command()
    async def stats(self, ctx, player: discord.Member = None):
        async with self.pool.acquire() as conn:
            if player is None:
                # Show leaderboard top 8
                records = await conn.fetch("""
                    SELECT * FROM stats ORDER BY wins DESC, array_length(br_placements,1) DESC LIMIT 8
                """)
                if not records:
                    await ctx.send("No stats available.")
                    return
                leaderboard_lines = []
                for idx, record in enumerate(records, start=1):
                    uid = record['user_id']
                    wins = record['wins']
                    br_placements = ", ".join(record['br_placements']) if record['br_placements'] else "None"
                    member = ctx.guild.get_member(int(uid))
                    mention = member.mention if member else f"<@{uid}>"
                    leaderboard_lines.append(f"**{idx}. {mention}** — Wins: {wins}, BR Placements: {br_placements}")
                leaderboard_text = "**🏆 Top 8 Players by Wins:**\n" + "\n".join(leaderboard_lines)
                await ctx.send(leaderboard_text)
            else:
                uid = str(player.id)
                record = await conn.fetchrow("SELECT * FROM stats WHERE user_id = $1", uid)
                if not record:
                    await ctx.send(f"No stats found for {player.display_name}.")
                    return
                wins = record['wins']
                br_placements = ", ".join(record['br_placements']) if record['br_placements'] else "None"
                events = ", ".join(record['events']) if record['events'] else "None"
                mention = player.mention
                await ctx.send(
                    f"**Stats for {mention}:**\n"
                    f"Wins: {wins}\n"
                    f"Battle Royal Placements: {br_placements}\n"
                    f"Events: {events}"
                )

    @commands.command()
    async def clearall(self, ctx, player: discord.Member):
        uid = str(player.id)
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM stats WHERE user_id=$1", uid)
        await ctx.send(f"All stats cleared for {player.display_name}.")

    @commands.command()
    async def clear_recent(self, ctx, player: discord.Member):
        uid = str(player.id)
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT * FROM stats WHERE user_id=$1", uid)
            if not record:
                await ctx.send(f"No stats found for {player.display_name}.")
                return
            br_placements = record['br_placements'] or []
            events = record['events'] or []

            removed_event = events.pop() if events else None
            removed_placement = br_placements.pop() if br_placements else None

            await conn.execute("""
                UPDATE stats SET br_placements=$1, events=$2 WHERE user_id=$3
            """, br_placements, events, uid)

            if removed_event or removed_placement:
                await ctx.send(f"Removed most recent event for {player.display_name}: event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}.")
            else:
                await ctx.send(f"No recent events to remove for {player.display_name}.")

class DiscordBot(commands.Bot):
    def __init__(self, pool):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.pool = pool
        self.logger = logging.getLogger(__name__)

    async def setup_hook(self):
        self.event_cog = EventCog(self, self.pool)
        await self.event_cog.init_db()
        await self.add_cog(self.event_cog)
        self.logger.info("Cog loaded.")

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Establishment Minigames"))
        self.logger.info("Bot is ready!")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ Command `{ctx.invoked_with}` not found. Use `!list` for commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument `{error.param.name}`. Use `!list {ctx.command}` for help.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument. Use `!list {ctx.command}` for help.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command cooldown: try again in {error.retry_after:.1f}s.")
        else:
            self.logger.error(f"Error in command {ctx.command}: {error}")
            await ctx.send("❌ Unexpected error occurred.")

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

async def main():
    import asyncio
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        return
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set.")
        return

    pool = await asyncpg.create_pool(DATABASE_URL)
    bot = DiscordBot(pool)
    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

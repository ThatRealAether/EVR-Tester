import discord
from flask import Flask
from threading import Thread
from discord.ext import commands
import os
import logging
import asyncio
import asyncpg

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

class EventCog(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    async def load_user_stats(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wins, br_placements, events FROM stats WHERE user_id = $1", user_id)
            if row:
                return {
                    "wins": row["wins"],
                    "br": row["br_placements"] or [],
                    "events": row["events"] or []
                }
            else:
                return {"wins": 0, "br": [], "events": []}

    async def save_user_stats(self, user_id, data):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stats (user_id, wins, br_placements, events) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    wins = EXCLUDED.wins,
                    br_placements = EXCLUDED.br_placements,
                    events = EXCLUDED.events
            """, user_id, data["wins"], data["br"], data["events"])

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def list(self, ctx):
        help_text = (
            "# __Bot Commands__\n"
            "- **!eventreg** - Log an event\n"
            " • Example: `!eventreg @User Cooking false 7/25`\n"
            " • Example: `!eventreg @User PVP true 1st 7/25`\n"
            "- **!stats [@user]** — Show stats for a user or yourself\n"
            "- **!clearall [@user]** — Clear all stats for a user\n"
            "- **!clear_recent [@user]** — Clear most recent stat for a user\n"
        )
        await ctx.send(help_text)

    @commands.command()
    async def eventreg(self, ctx, player: discord.Member, event_name: str, is_battle_royal: str, placement_or_date: str = None, date: str = None):
        is_br = is_battle_royal.lower() in ("true", "yes", "1", "y")
        uid = str(player.id)

        stats = await self.load_user_stats(uid)

        if is_br:
            if placement_or_date is None or date is None:
                await ctx.send("You must specify placement and date for a battle royal event. Example:\n`!eventreg @player event_name true 1st 7/25`")
                return
            placement = placement_or_date
            stats["br"].append(placement)
            stats["events"].append(f"{event_name} (Date: {date})")
            # Only count win if placement is "1st"
            if placement.lower() == "1st":
                stats["wins"] += 1
            await ctx.send(f"Recorded battle royal event **{event_name}** for {player.display_name} with placement {placement} on {date}.")
        else:
            date = placement_or_date
            if date is None:
                await ctx.send("You must specify the date for a non-battle royal event. Example:\n`!eventreg @player event_name false 7/25`")
                return
            stats["events"].append(f"{event_name} (Date: {date})")
            stats["wins"] += 1
            await ctx.send(f"Recorded non-battle royal event **{event_name}** for {player.display_name} on {date}.")

        await self.save_user_stats(uid, stats)

    @commands.command()
    async def stats(self, ctx, player: discord.Member = None):
        async with self.pool.acquire() as conn:
            if player is None:
                # Get all stats to show top 8
                rows = await conn.fetch("SELECT user_id, wins, br_placements FROM stats")
                if not rows:
                    await ctx.send("No stats available.")
                    return
                
                def sort_key(row):
                    wins = row["wins"] or 0
                    br_count = len(row["br_placements"] or [])
                    return (-wins, -br_count)

                sorted_rows = sorted(rows, key=sort_key)
                top_8 = sorted_rows[:8]

                leaderboard_lines = []
                for idx, row in enumerate(top_8, start=1):
                    user_id = row["user_id"]
                    member = ctx.guild.get_member(int(user_id))
                    display_name = member.display_name if member else "Unknown User"
                    wins = row["wins"]
                    br_placements = ", ".join(row["br_placements"]) if row["br_placements"] else "None"
                    leaderboard_lines.append(f"**{idx}. {display_name}** — Wins: {wins}, BR Placements: {br_placements}")

                leaderboard_text = "**🏆 Top 8 Players by Wins:**\n" + "\n".join(leaderboard_lines)
                await ctx.send(leaderboard_text)
                return

            uid = str(player.id)
            row = await conn.fetchrow("SELECT wins, br_placements, events FROM stats WHERE user_id = $1", uid)
            if not row:
                await ctx.send(f"No stats found for {player.display_name}.")
                return

            placements = ", ".join(row["br_placements"]) if row["br_placements"] else "None"
            events = ", ".join(row["events"]) if row["events"] else "None"

            await ctx.send(
                f"**Stats for {player.display_name}:**\n"
                f"Wins: {row['wins']}\n"
                f"Battle Royal Placements: {placements}\n"
                f"Events: {events}"
            )

    @commands.command()
    async def clearall(self, ctx, player: discord.Member):
        uid = str(player.id)
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM stats WHERE user_id = $1", uid)
            if result.endswith("DELETE 1"):
                await ctx.send(f"All stats cleared for {player.display_name}.")
            else:
                await ctx.send(f"No stats found for {player.display_name}.")

    @commands.command()
    async def clear_recent(self, ctx, player: discord.Member):
        uid = str(player.id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wins, br_placements, events FROM stats WHERE user_id = $1", uid)
            if not row:
                await ctx.send(f"No stats found for {player.display_name}.")
                return

            wins = row["wins"]
            br_placements = row["br_placements"] or []
            events = row["events"] or []

            removed_event = None
            removed_placement = None

            if events:
                removed_event = events.pop()
            if br_placements:
                removed_placement = br_placements.pop()

            # Adjust wins if removed placement was "1st"
            if removed_placement and removed_placement.lower() == "1st":
                wins = max(0, wins - 1)

            await conn.execute("""
                UPDATE stats SET wins = $1, br_placements = $2, events = $3 WHERE user_id = $4
            """, wins, br_placements, events, uid)

            if removed_event or removed_placement:
                await ctx.send(f"Removed most recent event for {player.display_name}: event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}.")
            else:
                await ctx.send(f"No recent events to remove for {player.display_name}.")

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.logger = logging.getLogger(__name__)
        self.pool = None

    async def setup_hook(self):
        # Connect to PostgreSQL here
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            self.logger.error("DATABASE_URL environment variable not set.")
            exit(1)

        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.add_cog(EventCog(self, self.pool))
        self.logger.info("Cog loaded and DB pool created.")

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

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        exit(1)
    bot = DiscordBot()

    keep_alive()
    asyncio.run(bot.start(TOKEN))

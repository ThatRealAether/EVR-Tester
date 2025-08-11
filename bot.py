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

    async def get_stats(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, wins, br_placements, events FROM stats")
            data = {}
            for row in rows:
                data[row['user_id']] = {
                    "wins": row['wins'],
                    "br_placements": row['br_placements'] or [],
                    "events": row['events'] or []
                }
            return data

    async def get_user_stats(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wins, br_placements, events FROM stats WHERE user_id=$1", user_id)
            if row:
                return {
                    "wins": row['wins'],
                    "br_placements": row['br_placements'] or [],
                    "events": row['events'] or []
                }
            else:
                return {"wins": 0, "br_placements": [], "events": []}

    async def save_user_stats(self, user_id, wins, br_placements_list, events_list):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stats (user_id, wins, br_placements, events) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                SET wins = EXCLUDED.wins,
                    br_placements = EXCLUDED.br_placements,
                    events = EXCLUDED.events
            """, user_id, wins, br_placements_list, events_list)

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

        stats = await self.get_user_stats(uid)
        wins = stats["wins"]
        br_placements = stats["br_placements"]
        events = stats["events"]

        if is_br:
            if placement_or_date is None or date is None:
                await ctx.send("You must specify placement and date for a battle royal event. Example:\n`!eventreg @player event_name true 1st 7/25`")
                return
            placement = placement_or_date
            br_placements.append(placement)
            events.append(f"{event_name} (Date: {date})")
            if placement.lower() == "1st":
                wins += 1
            await ctx.send(f"Recorded battle royal event **{event_name}** for {player.display_name} with placement {placement} on {date}.")
        else:
            date = placement_or_date
            if date is None:
                await ctx.send("You must specify the date for a non-battle royal event. Example:\n`!eventreg @player event_name false 7/25`")
                return
            events.append(f"{event_name} (Date: {date})")
            wins += 1
            await ctx.send(f"Recorded non-battle royal event **{event_name}** for {player.display_name} on {date}.")

        await self.save_user_stats(uid, wins, br_placements, events)

    @commands.command()
    async def stats(self, ctx, player: discord.Member = None):
        if player is None:
            # Show top 8 leaderboard
            stats = await self.get_stats()
            if not stats:
                await ctx.send("No stats found yet.")
                return

            def sort_key(item):
                uid, data = item
                wins = data.get("wins", 0)
                br_count = len(data.get("br_placements", []))
                return (-wins, -br_count)

            sorted_users = sorted(stats.items(), key=sort_key)
            top_8 = sorted_users[:8]

            leaderboard_lines = []
            for idx, (uid, data) in enumerate(top_8, start=1):
                member = ctx.guild.get_member(int(uid))
                # Mention user if cached, otherwise raw mention by ID
                mention = member.mention if member else f"<@{uid}>"
                wins = data.get("wins", 0)
                br_placements = ", ".join(data.get("br_placements", [])) if data.get("br_placements") else "None"
                leaderboard_lines.append(f"**{idx}. {mention}** — Wins: {wins}, BR Placements: {br_placements}")

            leaderboard_text = "**🏆 Top 8 Players by Wins:**\n" + "\n".join(leaderboard_lines)
            await ctx.send(leaderboard_text)
            return

        uid = str(player.id)
        data = await self.get_user_stats(uid)
        if not data or (data["wins"] == 0 and not data["br_placements"] and not data["events"]):
            await ctx.send(f"No stats found for {player.display_name}.")
            return

        placements = ", ".join(data["br_placements"]) if data["br_placements"] else "None"
        events = ", ".join(data["events"]) if data["events"] else "None"
        mention = player.mention
        await ctx.send(
            f"**Stats for {mention}:**\n"
            f"Wins: {data['wins']}\n"
            f"Battle Royal Placements: {placements}\n"
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
        stats = await self.get_user_stats(uid)
        if not stats or (stats["wins"] == 0 and not stats["br_placements"] and not stats["events"]):
            await ctx.send(f"No stats found for {player.display_name}.")
            return

        br_placements = stats["br_placements"]
        events = stats["events"]
        wins = stats["wins"]

        removed_event = events.pop() if events else None
        removed_placement = br_placements.pop() if br_placements else None

        # If the removed placement was "1st" and it was a BR event, decrease wins
        if removed_placement and removed_placement.lower() == "1st":
            wins = max(0, wins - 1)

        await self.save_user_stats(uid, wins, br_placements, events)
        await ctx.send(f"Removed most recent event for {player.display_name}: event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}.")

class DiscordBot(commands.Bot):
    def __init__(self, pool):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Important: enable member intent!
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.logger = logging.getLogger(__name__)
        self.pool = pool

    async def setup_hook(self):
        await self.add_cog(EventCog(self, self.pool))
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
    logging.basicConfig(level=logging.INFO)
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

    keep_alive()
    await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())

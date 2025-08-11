import discord
from discord.ext import commands
from discord import Embed, ui, Interaction
from flask import Flask
from threading import Thread
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

class LeaderboardView(ui.View):
    def __init__(self, ctx, stats, per_page=8):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.ctx = ctx
        self.stats = stats
        self.per_page = per_page
        self.page = 1
        self.sorted_users = sorted(
            stats.items(),
            key=lambda item: (-item[1].get("wins", 0), -len(item[1].get("br_placements", [])))
        )
        self.max_page = (len(self.sorted_users) - 1) // per_page + 1

        # Disable prev button initially
        self.prev_button.disabled = True
        if self.max_page <= 1:
            self.next_button.disabled = True

    async def update_embed(self):
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        page_users = self.sorted_users[start:end]

        embed = Embed(
            title=f"🏆 Top Players by Wins (Page {self.page}/{self.max_page})",
            description="",
            color=discord.Color.dark_teal()
        )

        for idx, (uid, data) in enumerate(page_users, start=start + 1):
            member = self.ctx.guild.get_member(int(uid))
            if not member:
                try:
                    member = await self.ctx.guild.fetch_member(int(uid))
                except:
                    member = None
            mention = member.mention if member else f"<@{uid}>"
            wins = data.get("wins", 0)
            br_placements = ", ".join(data.get("br_placements", [])) if data.get("br_placements") else "None"
            embed.description += f"**{idx}. {mention}** — Wins: {wins}, BR Placements: {br_placements}\n\n"

        return embed

    @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: Interaction, button: ui.Button):
        if self.page > 1:
            self.page -= 1
            embed = await self.update_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        # Disable buttons if on first page
        self.prev_button.disabled = self.page == 1
        self.next_button.disabled = False

    @ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: Interaction, button: ui.Button):
        if self.page < self.max_page:
            self.page += 1
            embed = await self.update_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        # Disable buttons if on last page
        self.next_button.disabled = self.page == self.max_page
        self.prev_button.disabled = False

class EventCog(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    async def get_stats(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, wins, br_placements, events, marathon_wins FROM stats")
            data = {}
            for row in rows:
                data[row['user_id']] = {
                    "wins": row['wins'],
                    "br_placements": row['br_placements'] or [],
                    "events": row['events'] or [],
                    "marathon_wins": row['marathon_wins'] or 0,
                }
            return data

    async def get_user_stats(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT wins, br_placements, events, marathon_wins FROM stats WHERE user_id=$1", user_id)
            if row:
                return {
                    "wins": row['wins'],
                    "br_placements": row['br_placements'] or [],
                    "events": row['events'] or [],
                    "marathon_wins": row['marathon_wins'] or 0,
                }
            else:
                return {"wins": 0, "br_placements": [], "events": [], "marathon_wins": 0}

    async def save_user_stats(self, user_id, wins, br_placements_list, events_list, marathon_wins):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stats (user_id, wins, br_placements, events, marathon_wins)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE
                SET wins = EXCLUDED.wins,
                    br_placements = EXCLUDED.br_placements,
                    events = EXCLUDED.events,
                    marathon_wins = EXCLUDED.marathon_wins
            """, user_id, wins, br_placements_list, events_list, marathon_wins)

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
            "- **!marathonset @User <number>** — Set Marathon Wins for a user\n"
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
        marathon_wins = stats["marathon_wins"]

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

        await self.save_user_stats(uid, wins, br_placements, events, marathon_wins)

    @commands.command()
    async def marathonset(self, ctx, player: discord.Member, count: int):
        uid = str(player.id)
        stats = await self.get_user_stats(uid)

        marathon_wins = count

        await self.save_user_stats(uid, stats['wins'], stats['br_placements'], stats['events'], marathon_wins)

        await ctx.send(f"Set Marathon Wins for {player.display_name} to {marathon_wins}.")

    @commands.command()
    async def stats(self, ctx, player: discord.Member = None):
        if player is None:
            stats = await self.get_stats()
            if not stats:
                await ctx.send("No stats found yet.")
                return

            view = LeaderboardView(ctx, stats)
            embed = await view.update_embed()
            await ctx.send(embed=embed, view=view)
            return

        uid = str(player.id)
        data = await self.get_user_stats(uid)
        if not data or (data["wins"] == 0 and not data["br_placements"] and not data["events"] and data["marathon_wins"] == 0):
            await ctx.send(f"No stats found for {player.display_name}.")
            return

        placements = ", ".join(data["br_placements"]) if data["br_placements"] else "None"
        events = ", ".join(data["events"]) if data["events"] else "None"
        marathon_wins = data["marathon_wins"]

        embed = Embed(
            title=f"Stats for {player.display_name}",
            color=discord.Color.dark_teal()
        )
        embed.add_field(name="Wins", value=str(data["wins"]), inline=False)
        embed.add_field(name="Battle Royal Placements", value=placements, inline=False)
        embed.add_field(name="Events", value=events, inline=False)
        embed.add_field(name="Marathon Wins", value=str(marathon_wins), inline=False)

        await ctx.send(embed=embed)

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
        marathon_wins = stats["marathon_wins"]

        removed_event = events.pop() if events else None
        removed_placement = br_placements.pop() if br_placements else None

        if removed_placement and removed_placement.lower() == "1st":
            wins = max(0, wins - 1)

        await self.save_user_stats(uid, wins, br_placements, events, marathon_wins)
        await ctx.send(f"Removed most recent event for {player.display_name}: event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}.")

class DiscordBot(commands.Bot):
    def __init__(self, pool):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Needed for member cache & fetch
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
            await ctx.send(f"What in the world is `{ctx.invoked_with}`. Maybe read !list sometime")
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

import discord
from flask import Flask
from threading import Thread
from discord.ext import commands
import json
import os
import logging

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
    def __init__(self, bot):
        self.bot = bot
        self.stats_file = "stats.json"
        self.user_stats = self.load_stats()

    def load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_stats(self):
        with open(self.stats_file, "w") as f:
            json.dump(self.user_stats, f, indent=4)

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
        """
        Usage:
        !eventreg @player event_name true 1st 7/25   # Battle royal with placement and date
        !eventreg @player event_name false 7/25      # Non-battle royal, date instead of placement
        """
        is_br = is_battle_royal.lower() in ("true", "yes", "1", "y")
        uid = str(player.id)

        if uid not in self.user_stats:
            self.user_stats[uid] = {"wins": 0, "br": [], "events": []}

        if is_br:
            if placement_or_date is None or date is None:
                await ctx.send("You must specify placement and date for a battle royal event. Example:\n`!eventreg @player event_name true 1st 7/25`")
                return
            placement = placement_or_date
            self.user_stats[uid]["br"].append(placement)
            self.user_stats[uid]["events"].append(f"{event_name} (Date: {date})")
            if placement.lower().startswith("1"):
                self.user_stats[uid]["wins"] += 1
            await ctx.send(f"Recorded battle royal event **{event_name}** for {player.display_name} with placement {placement} on {date}.")
        else:
            date = placement_or_date
            if date is None:
                await ctx.send("You must specify the date for a non-battle royal event. Example:\n`!eventreg @player event_name false 7/25`")
                return
            self.user_stats[uid]["events"].append(f"{event_name} (Date: {date})")
            self.user_stats[uid]["wins"] += 1
            await ctx.send(f"Recorded non-battle royal event **{event_name}** for {player.display_name} on {date}.")

        self.save_stats()

@commands.command()
async def stats(self, ctx, player: discord.Member = None):
    if not self.user_stats:
        await ctx.send("No stats found yet.")
        return

    def get_display_name(user_id: str):
        member = ctx.guild.get_member(int(user_id))
        return member.display_name if member else "Unknown User"

    if player is None:
        # Sort users by wins descending, then BR placements descending
        def sort_key(item):
            uid, data = item
            wins = data.get("wins", 0)
            br_count = len(data.get("br", []))
            return (-wins, -br_count)

        sorted_users = sorted(self.user_stats.items(), key=sort_key)
        top_8 = sorted_users[:8]
        if not top_8:
            await ctx.send("No stats available.")
            return

        leaderboard_lines = []
        for idx, (uid, data) in enumerate(top_8, start=1):
            name = get_display_name(uid)
            wins = data.get("wins", 0)
            br_placements = ", ".join(data.get("br", [])) if data.get("br") else "None"
            leaderboard_lines.append(f"**{idx}. {name}** — Wins: {wins}, BR Placements: {br_placements}")

        leaderboard_text = "**🏆 Top 8 Players by Wins:**\n" + "\n".join(leaderboard_lines)
        await ctx.send(leaderboard_text)
        return

    uid = str(player.id)
    if uid not in self.user_stats:
        await ctx.send(f"No stats found for {player.display_name}.")
        return
    data = self.user_stats[uid]
    placements = ", ".join(data["br"]) if data["br"] else "None"
    events = ", ".join(data["events"]) if data["events"] else "None"
    name = get_display_name(uid)
    await ctx.send(
        f"**Stats for {name}:**\n"
        f"Wins: {data['wins']}\n"
        f"Battle Royal Placements: {placements}\n"
        f"Events: {events}"
    )

    def get_display_name(self, ctx, user_id: int) -> str:
        member = ctx.guild.get_member(user_id)
        if member:
            return member.display_name
        else:
            return "Unknown User"

    @commands.command()
    async def clearall(self, ctx, player: discord.Member):
        uid = str(player.id)
        if uid in self.user_stats:
            del self.user_stats[uid]
            self.save_stats()
            await ctx.send(f"All stats cleared for {player.display_name}.")
        else:
            await ctx.send(f"No stats found for {player.display_name}.")

    @commands.command()
    async def clear_recent(self, ctx, player: discord.Member):
        uid = str(player.id)
        if uid not in self.user_stats:
            await ctx.send(f"No stats found for {player.display_name}.")
            return
        data = self.user_stats[uid]
        removed_event = data["events"].pop() if data["events"] else None
        removed_placement = data["br"].pop() if data["br"] else None
        self.save_stats()
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

    async def setup_hook(self):
        await self.add_cog(EventCog(self))
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        exit(1)
    bot = DiscordBot()
    
    keep_alive()
    bot.run(TOKEN)

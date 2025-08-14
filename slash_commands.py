# slash_commands.py
import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import re
from datetime import datetime

# ===== Game data =====
GAME_DATA = {
    "pizzeria survival": "## __Pizzeria Survival__\n"
                         "Pizzeria survival revolves around you surviving against a plethora of different monsters roaming around a pizzeria. Different monsters do different things so make sure to pay attention when they are explained.",
    "locate the spy": "## __Locate the Spy__\n"
                      "You and your peers are thrown into an abandoned facility with a catch, some of you are spies, or worse. Use the role you are assigned to either survive on your own, help everyone, or sabotage those around you. But make sure to leave in time before the core reactor explodes. If a spy is let on at the end, everyone loses and the spies win. Though, there may be others with different plans in mind.",
    "doppelgangers": "## __Doppelgangers__\n"
                     "Everyone is thrown into a facility where you need to get checked out by guards, your goal is to be let in the facility without getting gassed. 2-3 players will be assigned to be a guard and your goal is to let the citizens in, but keep the doppelgangers out.",
    "hide and seek": "## __Hide and Seek__\n"
                     "In hide and seek a monster roams around the area, your goal is to not get spotted to move on to the next round, or win. If you are spotted once you are most likely guaranteed to die.",
    "guessing game": "## __Guessing Game__\n"
                     "The host will think of a prompt, your goal is to guess what it is in 10-15 questions. The questions *have* to be yes or no questions, the host will not respond otherwise, and if you repeatedly mess up you die. Once the questions are used up, the host will call on someone random, they can discuss what they think with their peers but if you get it wrong, you die.",
    "property listing": "## __Property Listing__\n"
                        "The opposite of guessing game, you will be given a prompt and then you and your peers must come up with descriptors for said prompt. The more niche it is, the more points you get. But if you have to *really* stretch it to make it work, you get less points. capping out at 20. The person with the least points at the end of each round dies.",
    "cooking": "## __Cooking__\n"
               "Your goal is to survive as many rounds as possible; you will work with your fellow chefs to make it through said rounds. But it won't be so easy, there are monsters outside trying to stop your progress. They range from customers to the health inspector. Try to keep the floors clean and have good teamwork, you may be docked points for doing otherwise. You have 2 lives before its over.",
    "city rushdown": "## __City Rushdown__\n"
                    "The game takes place in a huge and booming city, except you are stuck on a platform. Your goal is to not die from electrocution, if the purple electricity happens to get passed to you, pass it to others by colliding with their bounding box.",
    "ghost hunting": "## __Ghost Hunting__\n"
                     "You are trapped in a facility with your peers, it doesn't matter if they die, all that matters is that *you* survive. Your goal is to capture as much paranormal activity as possible on your body \"camera\". This can range from a tray floating, random sounds, or the ghost itself, though it is recommended that you avoid seeing the ghost, those that do usually never live to tell the tale.",
    "hook chasers": "## __Hook Chasers__\n"
                   "Hook Chasers is all about aerial tag, everyone except one random person every round. The tagger's goal is to tag everyone, runners get points for time alive, the person with the least amount of points every round dies.",
    "karts": "## __Karts__\n"
             "You and your peers are placed onto a racetrack, your goal is to not be in one of the last 2 positions when you finish, if you are, you get eliminated from the event. Each track has its own obstacles that you need to avoid ranging from icy floors, to giant pinballs in the sky."
}

# ===== Helper function =====
def parse_event_date(event_str):
    match = re.search(r"\(Date:\s*(\d{1,2})/(\d{1,2})\)", event_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        return datetime(2000, month, day)
    else:
        return datetime.min

# ===== Slash commands cog =====
class SlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool

    # ----- Database functions -----
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

    # ----- Slash commands -----
    @app_commands.command(name="ping", description="Check if bot is alive.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @app_commands.command(name="list", description="Show list of commands.")
    async def list_commands(self, interaction: discord.Interaction):
        help_text = (
            "# __Bot Commands__\n"
            "- **/stats [user]** - Displays stats for all or a specific user\n"
            "- **/index** — Show list of game modes (select one to see description)\n"
            "- **/search <game_name>** — Show winners of a specific game mode\n"
            "- **/tlist** - Show team commands list\n"
        )
        await interaction.response.send_message(help_text, ephemeral=True)

    @app_commands.command(name="stats", description="Show stats for a user or all users.")
    @app_commands.describe(user="User to show stats for (optional)")
    async def stats(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        user_id = str(user.id) if user else None
        # Your full /stats implementation goes here (exactly like your original code)

    @app_commands.command(name="clearall", description="Clear all stats for a user.")
    @app_commands.describe(user="User to clear stats for")
    async def clearall(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        uid = str(user.id)
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM stats WHERE user_id=$1", uid)
        await interaction.followup.send(f"All stats cleared for {user.display_name}.")

    @app_commands.command(name="index", description="Show list of game modes.")
    async def index(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="EM Game Index",
            description="\n\n".join(f"• {name.title()}" for name in GAME_DATA.keys()),
            color=discord.Color.dark_teal()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="search", description="Search winners of a specific game mode.")
    @app_commands.describe(game_name="Game mode name to search for")
    async def search(self, interaction: discord.Interaction, game_name: str):
        await interaction.response.defer()
        # Your full /search implementation goes here (exactly like your original code)

# ===== Cog setup =====
async def setup(bot):
    await bot.add_cog(SlashCommands(bot))
    print("SlashCommands cog loaded successfully!")

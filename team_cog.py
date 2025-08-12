import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncpg

TEAM_EMOJIS = {
    "Chaos": "<:chaos:1404549946694307924>",
    "Revel": "<:revel:1404549965421871265>",
    "Hearth": "<:hearth:1404549986850443334>",
    "Honor": "<:honor:1404550005573943346>",
}

class TeamCog(commands.Cog):
    TEAM_EMOJIS = TEAM_EMOJIS

    def __init__(self, bot: commands.Bot, pool: asyncpg.Pool = None):
        self.bot = bot
        self.pool = pool
        self.tree = bot.tree

    async def cog_load(self):
        await self.bot.wait_until_ready()
        try:
            await self.tree.sync()
            print("[TeamCog] Slash commands synced.")
        except Exception as e:
            print(f"[TeamCog] Failed to sync slash commands: {e}")

    async def _send(self, interaction_or_ctx, content):
        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.send_message(content)
        else:
            await interaction_or_ctx.send(content)

    async def _register_team(self, interaction_or_ctx, team_name: str):
        if team_name not in self.TEAM_EMOJIS:
            msg = f"Invalid team name. Available teams: {', '.join(self.TEAM_EMOJIS.keys())}"
        else:
            msg = f"Registered to team {self.TEAM_EMOJIS[team_name]} {team_name}!"
        await self._send(interaction_or_ctx, msg)

    async def _show_team(self, interaction_or_ctx, member: discord.Member):
        # For example, just showing Chaos team always; replace with real logic as needed
        team_name = "Chaos"
        if team_name:
            emoji = self.TEAM_EMOJIS.get(team_name, "")
            msg = f"{member.display_name} is on team {emoji} {team_name}"
        else:
            msg = f"{member.display_name} is not registered to any team."
        await self._send(interaction_or_ctx, msg)

    @commands.command(name="registerteam")
    async def register_team_prefix(self, ctx, team_name: str):
        await self._register_team(ctx, team_name)

    @commands.command(name="team")
    async def show_team_prefix(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await self._show_team(ctx, member)

    @app_commands.command(name="registerteam", description="Register to a team.")
    @app_commands.describe(team_name="The name of the team you want to join.")
    async def register_team_slash(self, interaction: discord.Interaction, team_name: str):
        await self._register_team(interaction, team_name)

    @app_commands.command(name="team", description="Check a member's team.")
    @app_commands.describe(member="The member whose team you want to check.")
    async def show_team_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        await self._show_team(interaction, member)


async def setup(bot):
    # Pass your asyncpg pool here if you have one, or None
    pool = getattr(bot, "pool", None)
    await bot.add_cog(TeamCog(bot, pool))

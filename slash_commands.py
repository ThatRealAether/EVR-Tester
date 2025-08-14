import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

DATABASE_URL = "postgresql://postgres:CPaRkvVKWEJnUffjirtKNWDwTAhhPbjB@postgres.railway.internal:5432/railway"

class PaginationView(discord.ui.View):
    def __init__(self, pages, interaction):
        super().__init__(timeout=60)
        self.pages = pages
        self.index = 0
        self.interaction = interaction

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)


class SlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_db(self):
        return await asyncpg.connect(DATABASE_URL)

    @app_commands.command(name="stats", description="Show player stats")
    async def stats(self, interaction: discord.Interaction, player: str):
        conn = await self.get_db()
        data = await conn.fetch("SELECT * FROM stats WHERE player = $1", player)
        await conn.close()

        if not data:
            await interaction.response.send_message("No stats found.", ephemeral=True)
            return

        pages = []
        for row in data:
            embed = discord.Embed(title=f"Stats for {row['player']}", color=discord.Color.blue())
            embed.add_field(name="Score", value=row["score"])
            embed.add_field(name="Wins", value=row["wins"])
            pages.append(embed)

        await interaction.response.send_message(embed=pages[0], view=PaginationView(pages, interaction))

    @app_commands.command(name="index", description="Show the index list")
    async def index(self, interaction: discord.Interaction):
        conn = await self.get_db()
        data = await conn.fetch("SELECT * FROM index_table")
        await conn.close()

        if not data:
            await interaction.response.send_message("Index is empty.", ephemeral=True)
            return

        pages = []
        for row in data:
            embed = discord.Embed(title="Index Entry", description=row["entry"], color=discord.Color.green())
            pages.append(embed)

        await interaction.response.send_message(embed=pages[0], view=PaginationView(pages, interaction))

    @app_commands.command(name="search", description="Search the database")
    async def search(self, interaction: discord.Interaction, query: str):
        conn = await self.get_db()
        data = await conn.fetch("SELECT * FROM index_table WHERE entry ILIKE $1", f"%{query}%")
        await conn.close()

        if not data:
            await interaction.response.send_message("No results found.", ephemeral=True)
            return

        pages = []
        for row in data:
            embed = discord.Embed(title="Search Result", description=row["entry"], color=discord.Color.purple())
            pages.append(embed)

        await interaction.response.send_message(embed=pages[0], view=PaginationView(pages, interaction))


async def setup(bot):
    await bot.add_cog(SlashCommands(bot))

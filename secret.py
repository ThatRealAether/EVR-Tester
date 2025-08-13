import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def secret(self, ctx):
        """Lists the secret commands."""
        commands_list = [
            "!vivziepop @user",
            "!ibrokearule",
            "!killaether",
            "!omegaflowey"
        ]
        await ctx.send("Secret commands:\n" + "\n".join(commands_list))

    @commands.command(hidden=True)
    async def vivziepop(self, ctx, member: discord.Member):
        """Sends the... colorful message."""
        msg = (
            f"{member.mention} i fucking hope you FUCKING die because FUCK you "
            f"i FUCKING want you FUCKING dead because FUCK you I FUCKING WANT FUCKING YOU "
            f"FUCKING DEAD FUCKING RIGHT FUCKING NOW YOU FUCKING NERD"
        )
        await ctx.send(msg)

    @commands.command(hidden=True)
    async def ibrokearule(self, ctx, member: discord.Member):
        """Times out a user for 60 seconds."""
        try:
            await member.timeout(timedelta(seconds=60))
            await ctx.send(f"{member.mention} has been timed out for 60 seconds.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout that user.")
        except discord.HTTPException:
            await ctx.send("Failed to timeout the user.")

    @commands.command(hidden=True)
    async def killaether(self, ctx):
        """Sends 'i agree'."""
        await ctx.send("i agree")

    @commands.command(hidden=True)
    async def omegaflowey(self, ctx):
        """Sends an image."""
        await ctx.send("https://i.imgur.com/xzIaiDz.png")


async def setup(bot):
    await bot.add_cog(Secret(bot))

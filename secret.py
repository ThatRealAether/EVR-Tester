import discord
from discord.ext import commands

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def secret(self, ctx):
        commands_list = (
            "**!vivziepop**\n"
            "**!ibrokearule**\n"
            "**!killaether**\n"
            "**!omegaflowey**"
        )
        await ctx.send(commands_list)

    @commands.command()
    async def vivziepop(self, ctx):
        author_mention = ctx.author.mention
        message = (
            f"{author_mention} i fucking hope you FUCKING die because FUCK you i FUCKING want "
            f"ou FUCKING dead because FUCK you I FUCKING WANT FUCKING YOU FUCKING DEAD "
            f"FUCKING RIGHT FUCKING NOW YOU FUCKING NERD"
        )
        await ctx.send(message)

    @commands.command()
    async def ibrokearule(self, ctx):
        try:
            await ctx.author.timeout(duration=60, reason="ibrokearule command used")
            await ctx.send(f"{ctx.author.mention}, you have been timed out for 60 seconds.")
        except Exception:
            await ctx.send(f"Could not timeout {ctx.author.mention}. Do I have the right permissions?")

    @commands.command()
    async def killaether(self, ctx):
        await ctx.send("i agree")

    @commands.command()
    async def omegaflowey(self, ctx):
        image_url = "https://i.imgur.com/xzIaiDz.png"
        await ctx.send(image_url)

async def setup(bot):
    await bot.add_cog(Secret(bot))

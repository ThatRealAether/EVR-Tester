import discord
from discord.ext import commands
from datetime import datetime, timedelta

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def secret(self, ctx):
        commands_list = (
            "**!vivziepop**\n\n"
            "**!ibrokearule**\n\n"
            "**!killaether**\n\n"
            "**!omegaflowey**\n\n"
            "**!imstrong**"
        )
        await ctx.send(commands_list)

    @commands.command()
    async def vivziepop(self, ctx):
        author_mention = ctx.author.mention
        message = (
            f"{author_mention} i fucking hope you FUCKING die because FUCK you i FUCKING want "
            f"you FUCKING dead because FUCK you I FUCKING WANT FUCKING YOU FUCKING DEAD "
            f"FUCKING RIGHT FUCKING NOW YOU FUCKING NERD"
        )
        await ctx.send(message)

    @commands.command()
    async def ibrokearule(self, ctx):
    try:
        until = datetime.utcnow() + timedelta(seconds=60)
        await ctx.author.timeout(until=until, reason="ibrokearule command used")
        await ctx.send(f"{ctx.author.mention}, you've been punished.")
        except Exception:
            await ctx.send(f"Can't timeout the bozo named {ctx.author.mention}. Idiot.")

    @commands.command()
    async def killaether(self, ctx):
        await ctx.send("i agree")

    @commands.command()
    async def omegaflowey(self, ctx):
        image_url = "https://i.imgur.com/xzIaiDz.png"
        await ctx.send(image_url)

    @commands.command()
    async def imstrong(self, ctx):
        gif_url = "https://tenor.com/view/goku-prowler-goku-goku-mad-goku-dbs-dbs-gif-11120329515669448575"
        await ctx.send(gif_url)

async def setup(bot):
    await bot.add_cog(Secret(bot))

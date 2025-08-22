from datetime import timedelta
import discord
from discord.ext import commands
from discord.utils import utcnow
import random

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def secret(self, ctx):
        commands_list = (
            "**!vivziepop**\n"
            "**!ibrokearule**\n"
            "**!killaether**\n"
            "**!omegaflowey**\n"
            "**!imstrong**\n"
            "**!rannum**"
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
            until = utcnow() + timedelta(seconds=60)
            await ctx.author.timeout(until)
            await ctx.send("LOSER IMAGINE BREAKING A RULE LMAOOOO")
        except discord.Forbidden:
            await ctx.send("I can't time you out, idiot")
        except discord.HTTPException:
            await ctx.send("I don't think you *really* broke a rule, did you?")

    @commands.command()
    async def superman(self, ctx):
        try:
            until = utcnow() + timedelta(seconds=604800)
            await ctx.author.timeout(until)
            await ctx.send("IMBOUTAKUUUUUUUUU")
        except discord.Forbidden:
            await ctx.send("no :(")
        except discord.HTTPException:
            await ctx.send("I don't think you *really* broke a rule, did you?")

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

    @commands.command()
    async def hi(self, ctx):
        await ctx.send("i hope you fucking die")

    @commands.command()
    async def rannum(self, ctx):
        num = random.randint(1, 10**30)
        await ctx.send(f"{num}")

async def setup(bot):
    await bot.add_cog(Secret(bot))

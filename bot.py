from flask import Flask
from threading import Thread
import discord
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

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

STATS_FILE = "user_stats.json"

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")

@bot.command()
async def stats(ctx):
    stats = load_stats()
    sorted_stats = sorted(stats.items(), key=lambda x: (-x[1].get("wins", 0), -x[1].get("battle_royal", 0)))
    
    embed = discord.Embed(title="EVR Stats", color=discord.Color.green())
    for user_id, data in sorted_stats:
        wins = data.get("wins", 0)
        battle_royal = data.get("battle_royal", 0)
        embed.add_field(name=f"<@{user_id}>", value=f"Wins: {wins} | Battle Royals: {battle_royal}", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def add_win(ctx, member: discord.Member):
    stats = load_stats()
    user_id = str(member.id)
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "battle_royal": 0}
    stats[user_id]["wins"] += 1
    save_stats(stats)
    await ctx.send(f"Added a win for <@{user_id}>!")

@bot.command()
async def add_br(ctx, member: discord.Member):
    stats = load_stats()
    user_id = str(member.id)
    if user_id not in stats:
        stats[user_id] = {"wins": 0, "battle_royal": 0}
    stats[user_id]["battle_royal"] += 1
    save_stats(stats)
    await ctx.send(f"Added a Battle Royal placement for <@{user_id}>!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        exit(1)

    keep_alive()
    bot.run(TOKEN)

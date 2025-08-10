import os
import logging
import sqlite3
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

DB_FILE = "stats.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            user_id TEXT PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            battle_royal INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def update_stat(user_id, stat_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"INSERT INTO stats (user_id, {stat_type}) VALUES (?, 1) "
              f"ON CONFLICT(user_id) DO UPDATE SET {stat_type} = {stat_type} + 1", (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, wins, battle_royal FROM stats ORDER BY wins DESC, battle_royal DESC")
    rows = c.fetchall()
    conn.close()
    return rows

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")

@bot.command()
async def stats(ctx):
    stats_data = get_stats()
    embed = discord.Embed(title="EVR Stats", color=discord.Color.green())
    for user_id, wins, br in stats_data:
        embed.add_field(name=f"<@{user_id}>", value=f"Wins: {wins} | Battle Royals: {br}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def add_win(ctx, member: discord.Member):
    update_stat(str(member.id), "wins")
    await ctx.send(f"Added a win for {member.mention}!")

@bot.command()
async def add_br(ctx, member: discord.Member):
    update_stat(str(member.id), "battle_royal")
    await ctx.send(f"Added a Battle Royal for {member.mention}!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        exit(1)
    keep_alive()
    bot.run(TOKEN)

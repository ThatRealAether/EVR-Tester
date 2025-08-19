import discord
from discord import ui
from flask import Flask
from threading import Thread
from discord.ext import commands
import os
import logging
import asyncio
import json
import asyncpg
import re
from team_cog import TeamCog
from datetime import datetime

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

GAME_DATA = {
    "Horror": {
        "pizzeria survival": "## __Pizzeria Survival__\n"
                "Pizzeria Survival revolves around you surviving against a plethora of different monsters roaming around a pizzeria. Different monsters do different things so make sure to pay attention when they are explained.",
        "hide and seek": "## __Hide and Seek__\n"
                "In hide and seek a monster roams around the area, your goal is to not get spotted to move on to the next round, or win. If you are spotted once you are most likely guaranteed to die.",
        "ghost hunting": "## __Ghost Hunting__\n"
                "You are trapped in a facility with your peers, it doesn't matter if they die, all that matters is that *you* survive. Your goal is to capture as much paranormal activity as possible on your body \"camera\". This can range from a tray floating, random sounds, or the ghost itself, though it is recommended that you avoid seeing the ghost, those that do usually never live to tell the tale.",
        "animation scurry": "## __Animation Scurry__\n"
                "You are trapped with your peers in Animation Alley from Bendy and the Ink Machine, it does not matter if you help your friends or not, just stay alive no matter the cost, multiple threats are hunting you down as well."
        "liminality": "## __Liminality__\n"
                "You and everyone else present is thrown into a liminal space with a monster lurking around the premises, try to stay quiet and low to the ground, other instructions are given by the bot that roams those halls."
    },
    "Every Man For Himself": {
        "doppelgangers": "## __Doppelgangers__\n"
                "Everyone is thrown into a facility where you need to get checked out by guards, your goal is to be let in the facility without getting gassed. 2-3 players will be assigned to be a guard and your goal is to let the citizens in, but keep the doppelgangers out.",
        "troll on the bridge": "## __Troll on the Bridge__\n"
                "You and your peers are at the start of a bridge trying to cross it to get into a facility. But, something named *Helper Bot* is blocking your path, one by one you must go up andn convince him to pass, succeed, and you make it through, fail, and you are killed. **DO NOT USE WINS AS AN ARGUEMENT TO GET INSIDE, THINK OF IT AS GETTING INTO CHARACTER**."
        "property listing": "## __Property Listing__\n"
                "The opposite of guessing game, you will be given a prompt and then you and your peers must come up with descriptors for said prompt. The more niche it is, the more points you get. But if you have to *really* stretch it to make it work, you get less points. capping out at 20. The person with the least points at the end of each round dies.",
        "city rushdown": "## __City Rushdown__\n"
                "The game takes place in a huge and booming city, except you are stuck on a platform. Your goal is to not die from electrocution, if the purple electricity happens to get passed to you, pass it to others by colliding with their bounding box.",
        "hook chasers": "## __Hook Chasers__\n"
                "Hook Chasers is all about aerial tag, everyone except one random person every round. The tagger's goal is to tag everyone, the runner's goal is to run away, the time for each round ranges from 8-15 minutes depending on player count. The tagger gets points for tagging people, runners get points for time alive, the person with the least amount of points every round dies.",
        "karts": "## __Karts__\n"
                "You and your peers are placed onto a racetrack, your goal is to not be in one of the last 2 positions when you finish, if you are, you get eliminated from the event. Each track has its own obstacles that you need to avoid ranging from icy floors, to giant pinballs in the sky."
    },
    "Team Based": {
        "locate the spy": "## __Locate the Spy__\n"
                "You and your peers are thrown into an abandoned facility with a catch, some of you are spies, or worse. Use the role you are assigned to either survive on your own, help everyone, or sabotage those around you. But make sure to leave in time before the core reactor explodes. If a spy is let on at the end, everyone loses and the spies win. Though, there may be others with different plans in mind.",
        "cooking": "## __Cooking__\n"
                "Your goal is to survive as many rounds as possible; you will work with your fellow chefs to make it through said rounds. But it won't be so easy, there are monsters outside trying to stop your progress. They range from customers to the health inspector. Try to keep the floors clean and have good teamwork, you may be docked points for doing otherwise. You have 2 lives before its over.",
        "team attack": "## __Team Attack__\n"
                "Team Attack is an altered version of locate the spy but instead of there being spies you have to locate, you are split into teams. There are many exclusive roles to this mode, your goal is to beat the other team by taking all of them out, coordinate with your team and team leader to best use your abilities and plan on how to take out the other team."
        "competitive cooking": "## __Competitive Cooking__\n"
                "Your goal is to work with the team you have been assigned to out-cook the other team! The opposing team gets eliminated, doesn't matter about the team size, ranging from 2 all the way to 8, just come out on top."
        "acting": "## __Acting__\n"
                "You will be grouped into teams with other people, the teams range from sizes of 2 - 4. Your goal is to follow the prompt but to ALSO be entertaining! If you fail either the host will decide, or the audience will vote for you to move onto the next round or not."
        "guessing game": "## __Guessing Game__\n"
                "The host will think of a prompt, your goal is to guess what it is in 10-15 questions. The questions *have* to be yes or no questions, the host will not respond otherwise, and if you repeatedly mess up you die. Once the questions are used up, the host will call on someone random, they can discuss what they think with their peers but if you get it wrong, you die.",
    }
}

class GameModal(discord.ui.Modal, title="Look up a Game"):
    game_name = discord.ui.TextInput(
        label="Enter a game name",
        placeholder="e.g. Hide and Seek",
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        name = self.game_name.value.lower()
        found = None
        for category, games in GAME_DATA.items():
            if name in games:
                found = (category, games[name])
                break

        if found:
            category, desc = found
            embed = discord.Embed(
                title=f"EM Game Index: {name.title()}",
                description=desc,
                color=discord.Color.dark_teal()
            )
            embed.set_footer(text=f"Category: {category}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ Could not find a game called **{self.game_name.value}**.",
                ephemeral=True
            )

def parse_event_date(event_str):
    match = re.search(r"\(Date:\s*(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\)", event_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else datetime.now().year
        return datetime(year, month, day)
    else:
        return datetime.min

class EventCog(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    class ListView(ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=180)
            self.ctx = ctx
            self.page = 0
            self.pages = [
                ("Bot Commands", (
                    "# __Bot Commands__\n"
                    "- **!stats** - Displays the stats of all users\n"
                    "- **!stats [@user]** - Displays the stats of a specific user\n"
                    "- **!index** — Show list of game modes (reply with name to see description)\n"
                    "- **!search <game name>** — Show winners of a specific game mode\n"
                    "- **!allevents [@user]** - Lists every event registered under a user\n"
                    "- **!esinfo** - lists the credits and montage for Establishment Survival"
                )),
                ("Team Commands", (
                    "# __Team Commands__\n"
                    "- **!join <team_name>** - Join a preset team (Chaos, Revel, Hearth, Honor). Must have at least one event.\n"
                    "- **!leave** - Leave your current team.\n"
                    "- **!teamstats [team_name]** - Show stats of a team or your own team if no name provided.\n"
                    "- **!leaderboard** - Show leaderboard of all teams by points.\n"
                )),
                ("Secret Commands", (
                    "# __Secret Commands__\n"
                    "**!vivziepop**\n"
                    "**!ibrokearule**\n"
                    "**!killaether**\n"
                    "**!omegaflowey**\n"
                    "**!imstrong**\n"
                    "**!rannum**"
                ))
            ]
            self.update_buttons()

        def update_buttons(self):
            pass

        async def get_embed(self):
            title, text = self.pages[self.page]
            embed = discord.Embed(
                title=f"{title} (Page {self.page + 1}/{len(self.pages)})",
                description=text,
                color=discord.Color.dark_teal()
            )
            return embed

        @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
        async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
            self.page = (self.page - 1) % len(self.pages)
            embed = await self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)

        @ui.button(label="Next", style=discord.ButtonStyle.blurple)
        async def next_button(self, interaction: discord.Interaction, button: ui.Button):
            self.page = (self.page + 1) % len(self.pages)
            embed = await self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    async def save_user_stats(self, uid, wins, br_placements, events, marathon_wins):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO stats (user_id, wins, br_placements, events, marathon_wins)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE
                SET wins = EXCLUDED.wins,
                    br_placements = EXCLUDED.br_placements,
                    events = EXCLUDED.events,
                    marathon_wins = EXCLUDED.marathon_wins
                """,
                uid, wins, br_placements, events, marathon_wins
            )

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
                "SELECT wins, br_placements, events, marathon_wins FROM stats WHERE user_id=$1",
                user_id
            )
            if row:
                br_placements = row['br_placements'] or []
                events = row['events'] or []

                br_wins = sum(1 for placement in br_placements if placement == "1st")
                total_wins = len(events) + br_wins

                return {
                    "wins": total_wins,
                    "br_placements": br_placements,
                    "events": events,
                    "marathon_wins": row['marathon_wins'] or 0,
                }
            else:
                return {"wins": 0, "br_placements": [], "events": [], "marathon_wins": 0}


    @commands.command()
    async def list(self, ctx):
        view = self.ListView(ctx)
        embed = await view.get_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def esinfo(self, ctx):
        credit_text = (
            "# __Credits & Montage__\n"
            "[Full Establishment Survival Credits](https://docs.google.com/document/d/1KOF-V0HDE6PwnxB5CD_4hyK4OCy4nDYxvINBdF2GX1g/edit?usp=sharing)\n"
            "-# This is a google document listing all of the credits for Establishment Survival ranging from worlds, to music, to helpers\n\n"
            "[Establishment Survival Clip Montage](https://youtu.be/1DBn-YMvkvw)\n"
            "-# This is a youtube video containing all of ES' best moments"
        )
        await ctx.send(credit_text, suppress_embeds=True)
    
    @commands.command()
    async def devlist(self, ctx):
        dev_text = (
            "# __Dev Commands__\n"
            "- **!eventreg** - Log an event\n"
            "- **!bulkreg** - Same format as !eventreg minus br logic\n"
            " `• Example: !eventreg @User Cooking false 7/25`\n"
            " `• Example: !eventreg @User PVP true 1st 7/25`\n"
            "- **!editreg** - Edit an entry of an event\n"
            " `• Example: !editreg @User Cooking 5/6 => Cooking 5/6/2024`\n"
            "- **!clearall [@user]** — Clear all stats for a user\n"
            "- **!clearrec [@user]** — Clear most recent stat for a user"
        )
        await ctx.send(dev_text)

    @commands.command()
    async def eventreg(self, ctx, player: discord.Member, event_name: str, is_battle_royal: str, placement_or_date: str = None, date: str = None):
        is_br = is_battle_royal.lower() in ("true", "yes", "1", "y")
        uid = str(player.id)
        stats = await self.get_user_stats(uid)
        wins = stats["wins"]
        br_placements = stats["br_placements"]
        events = stats["events"]
        marathon_wins = stats["marathon_wins"]

        if is_br:
            if placement_or_date is None or date is None:
                await ctx.send("You must specify placement and date for a battle royal event. Example:\n!eventreg @player event_name true 1st 7/25")
                return
            placement = placement_or_date
            br_placements.append(placement)
            events.append(f"{event_name} (Date: {date})")
            if placement.lower() == "1st":
                wins += 1
            await ctx.send(f"Recorded battle royal event **{event_name}** for {player.display_name} with placement {placement} on {date}.")
        else:
            date = placement_or_date
            if date is None:
                await ctx.send("You must specify the date for a non-battle royal event. Example:\n!eventreg @player event_name false 7/25")
                return
            events.append(f"{event_name} (Date: {date})")
            wins += 1
            await ctx.send(f"Recorded non-battle royal event **{event_name}** for {player.display_name} on {date}.")

        await self.save_user_stats(uid, wins, br_placements, events, marathon_wins)

    @commands.command()
    async def editreg(self, ctx, player: discord.Member, *, args: str):
        uid = str(player.id)

        if "=>" not in args:
            await ctx.send("You must separate the old and new event strings with =>.")
            return

        old_event_str, new_event_str = map(str.strip, args.split("=>", 1))
        stats = await self.get_user_stats(uid)
        events = stats["events"]

        date_pattern = r"\(?Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})\)?"

        def normalize_event(e):
            return re.sub(r"\(Date:\s*", "(", e).replace(")", "").strip()

        normalized_old = normalize_event(old_event_str)

        index = None
        if old_event_str in events:
            index = events.index(old_event_str)
        else:
            for i, e in enumerate(events):
                if normalize_event(e) == normalized_old:
                    index = i
                    break

        if index is None:
            await ctx.send(f"Could not find the event {old_event_str} in {player.display_name}'s events.")
            return

        events[index] = new_event_str
        await self.save_user_stats(uid, stats["wins"], stats["br_placements"], events, stats["marathon_wins"])
        await ctx.send(f"Updated event for {player.display_name}:\n{old_event_str} → {new_event_str}")


    @commands.command()
    async def marathonset(self, ctx, player: discord.Member, count: int):
        uid = str(player.id)
        stats = await self.get_user_stats(uid)
        marathon_wins = count
        await self.save_user_stats(uid, stats['wins'], stats['br_placements'], stats['events'], marathon_wins)
        await ctx.send(f"Set Marathon Wins for {player.display_name} to {marathon_wins}.")

    @commands.command()
    async def allevents(self, ctx, player: discord.Member):
        uid = str(player.id)
        data = await self.get_user_stats(uid)

        if not data or not data["events"]:
            await ctx.send(f"No events found for {player.display_name}.")
            return

        events_list = data["events"]
        display_events = ""
        for e in events_list:
            display_events += f"• {e}\n"

        embed = discord.Embed(
            title=f"All Events for {player.display_name}",
            description=display_events,
            color=discord.Color.dark_teal()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx, player: discord.Member = None):
        team_cog = self.bot.get_cog("TeamCog")

        if player is None:
            stats = await self.get_stats()
            if not stats:
                await ctx.send("No stats found yet.")
                return

            sorted_users = sorted(
                stats.items(),
                key=lambda item: (-item[1].get("wins", 0), -len(item[1].get("br_placements", [])))
            )
            per_page = 8
            max_page = (len(sorted_users) - 1) // per_page + 1

            class StatsLeaderboardView(ui.View):
                def __init__(self):
                    super().__init__(timeout=180)
                    self.page = 1
                    self.prev_button.disabled = True
                    if max_page <= 1:
                        self.next_button.disabled = True

                async def update_embed(self):
                    start = (self.page - 1) * per_page
                    end = start + per_page
                    page_users = sorted_users[start:end]
                    embed = discord.Embed(
                        title=f"🏆 Top Players by Wins (Page {self.page}/{max_page})",
                        description="",
                        color=discord.Color.dark_teal()
                    )
                    for idx, (uid, data) in enumerate(page_users, start=start + 1):
                        member = ctx.guild.get_member(int(uid))
                        if not member:
                            try:
                                member = await ctx.guild.fetch_member(int(uid))
                            except:
                                member = None
                        mention = member.mention if member else f"<@{uid}>"
                        team_display = ""
                        if team_cog:
                            team_id = await team_cog.get_user_team(uid)
                            if team_id is not None:
                                team_name = await team_cog.get_team_name_by_id(team_id)
                                if team_name:
                                    emoji = team_cog.TEAM_EMOJIS.get(team_name)
                                    if emoji:
                                        team_display = f"{emoji} {team_name} | "
                        wins = data.get("wins", 0)
                        br_placements = ", ".join(data.get("br_placements", [])) if data.get("br_placements") else "None"
                        embed.description += f"**{idx}. {team_display}{mention}** — Wins: {wins}, BR Placements: {br_placements}\n\n"
                    return embed

                @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
                async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
                    if self.page > 1:
                        self.page -= 1
                        self.prev_button.disabled = self.page == 1
                        self.next_button.disabled = False
                        embed = await self.update_embed()
                        await interaction.response.edit_message(embed=embed, view=self)

                @ui.button(label="Next", style=discord.ButtonStyle.blurple)
                async def next_button(self, interaction: discord.Interaction, button: ui.Button):
                    if self.page < max_page:
                        self.page += 1
                        self.next_button.disabled = self.page == max_page
                        self.prev_button.disabled = False
                        embed = await self.update_embed()
                        await interaction.response.edit_message(embed=embed, view=self)

            view = StatsLeaderboardView()
            embed = await view.update_embed()
            await ctx.send(embed=embed, view=view)

        else:
            uid = str(player.id)
            data = await self.get_user_stats(uid)
            if not data or (data["wins"] == 0 and not data["br_placements"] and not data["events"] and data["marathon_wins"] == 0):
                await ctx.send(f"No stats found for {player.display_name}.")
                return

            team_display = ""
            if team_cog:
                team_id = await team_cog.get_user_team(uid)
                if team_id is not None:
                    team_name = await team_cog.get_team_name_by_id(team_id)
                    if team_name:
                        emoji = team_cog.TEAM_EMOJIS.get(team_name.lower())
                        if emoji:
                            team_display = f"{emoji} {team_name} "

            placements = ", ".join(data["br_placements"]) if data["br_placements"] else "None"
            events_list = data["events"] if data["events"] else []
            marathon_wins = data["marathon_wins"]

            max_events_display = 10
            events_to_show = events_list[-max_events_display:][::-1]
            display_events = "\n".join(f"• {e}" for e in events_to_show)
            remaining = len(events_list) - max_events_display
            if remaining > 0:
                display_events += f"\n+{remaining} more..."

            embed = discord.Embed(
                title=f"Stats for {team_display}{player.display_name}",
                color=discord.Color.dark_teal()
            )
            embed.add_field(name="Wins", value=str(data['wins']), inline=False)
            embed.add_field(name="Battle Royal Placements", value=placements, inline=False)
            embed.add_field(name="Events", value=display_events if display_events else "None", inline=False)
            if marathon_wins > 0:
                embed.add_field(name="Marathon Wins", value=str(marathon_wins), inline=False)

            await ctx.send(embed=embed)

    @commands.command()
    async def clearall(self, ctx, player: discord.Member):
        uid = str(player.id)
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM stats WHERE user_id=$1", uid)
        await ctx.send(f"All stats cleared for {player.display_name}.")

    @commands.command()
    async def bulkreg(self, ctx, *args):
        if len(args) < 3:
            await ctx.send("Usage: !bulkreg @user1 @user2 ... EventName Date")
            return

        date = args[-1]
        event_name = args[-2]
        players = []
        for mention in args[:-2]:
            try:
                member = await commands.MemberConverter().convert(ctx, mention)
                players.append(member)
            except:
                continue

        if len(players) == 0:
            await ctx.send(f"Registered **{event_name}** for Casper the Ghost on {date}. SPECIFY USERS DUMBASS :sob:")
            return
        if len(players) == 1:
            await ctx.send("Please use !eventreg for single wins.")
            return

        event_entry = f"{event_name} (Date: {date})"
        for player in players:
            uid = str(player.id)
            stats = await self.get_user_stats(uid)
            wins = stats["wins"]
            br_placements = stats["br_placements"]
            events = stats["events"]
            marathon_wins = stats["marathon_wins"]

            events.append(event_entry)
            wins += 1
            await self.save_user_stats(uid, wins, br_placements, events, marathon_wins)

        mentions_text = "\n• ".join(p.mention for p in players)
        await ctx.send(f"Recorded **{event_name}** for the following users on {date}:\n• {mentions_text}")


    @commands.command()
    async def clearrec(self, ctx, player: discord.Member):
        uid = str(player.id)
        stats = await self.get_user_stats(uid)
        if not stats or (stats["wins"] == 0 and not stats["br_placements"] and not stats["events"]):
            await ctx.send(f"No stats found for {player.display_name}.")
            return

        br_placements = stats["br_placements"]
        events = stats["events"]
        wins = stats["wins"]
        marathon_wins = stats["marathon_wins"]

        removed_event = events.pop() if events else None
        removed_placement = br_placements.pop() if br_placements else None
        if removed_placement and removed_placement.lower() == "1st":
            wins = max(0, wins - 1)

        await self.save_user_stats(uid, wins, br_placements, events, marathon_wins)
        await ctx.send(
            f"Removed most recent event for {player.display_name}: "
            f"event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}."
        )


    @commands.command()
    async def index(self, ctx):
        
        categories = list(GAME_DATA.keys())
        page = 0

        def make_embed(page_index):
            cat = categories[page_index]
            games = GAME_DATA[cat]
            embed = discord.Embed(
                title=f"EM Game Index: {cat}",
                description="\n".join(f"• {name.title()}" for name in games.keys()),
                color=discord.Color.dark_teal()
            )
            embed.set_footer(text=f"Page {page_index + 1}/{len(categories)}")
            return embed

        message = await ctx.send(embed=make_embed(page))

        class IndexView(discord.ui.View):
            def __init__(self, ctx, message):
                super().__init__(timeout=60)
                self.ctx = ctx
                self.message = message
                self.page = 0

            async def update_embed(self, interaction=None):
                embed = make_embed(self.page)
                if interaction:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await self.message.edit(embed=embed, view=self)

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("This isn’t your session!", ephemeral=True)
                self.page = (self.page - 1) % len(categories)
                await self.update_embed(interaction)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("This isn’t your session!", ephemeral=True)
                self.page = (self.page + 1) % len(categories)
                await self.update_embed(interaction)

            @discord.ui.button(label="Look Up Game", style=discord.ButtonStyle.green)
            async def lookup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.ctx.author:
                    return await interaction.response.send_message("This isn’t your session!", ephemeral=True)
                await interaction.response.send_modal(GameModal())

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                try:
                    await self.message.edit(content="⌛ This index session has expired. Use `!index` again.", view=self)
                except:
                    pass

        view = IndexView(ctx, message)
        await view.update_embed(None)

    @commands.command()
    async def search(self, ctx, *, game_name: str):
        game_name_lower = game_name.lower()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, events FROM stats")

        matched_entries = []
        for row in rows:
            user_id = row['user_id']
            events = row['events'] or []
            for event_str in events:
                if game_name_lower in event_str.lower():
                    event_date = parse_event_date(event_str)
                    matched_entries.append((user_id, event_str, event_date))

        if not matched_entries:
            await ctx.send(f"No wins found for event matching '{game_name}'.")
            return

        matched_entries.sort(key=lambda x: x[2] or datetime.min, reverse=True)

        per_page = 8
        max_page = (len(matched_entries) - 1) // per_page + 1

        class SearchView(ui.View):
            def __init__(self):
                super().__init__(timeout=180)
                self.page = 1
                self.per_page = per_page
                self.max_page = max_page
                self.user_cache = {}
                self.prev_button.disabled = True
                if self.max_page <= 1:
                    self.next_button.disabled = True

            async def update_embed(self):
                start = (self.page - 1) * self.per_page
                end = start + self.per_page
                page_entries = matched_entries[start:end]

                embed = discord.Embed(
                    title=f"Search Results for '{game_name}' (Page {self.page}/{self.max_page})",
                    description="",
                    color=discord.Color.dark_teal()
                )
                for idx, (uid, ev_str, _) in enumerate(page_entries, start=start + 1):
                    if uid in self.user_cache:
                        member = self.user_cache[uid]
                    else:
                        member = ctx.guild.get_member(int(uid))
                        if not member:
                            try:
                                member = await ctx.guild.fetch_member(int(uid))
                            except:
                                member = None
                        self.user_cache[uid] = member
                    mention = member.mention if member else f"<@{uid}>"
                    embed.description += f"**{idx}. {mention}** — {ev_str}\n"
                return embed

            @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
            async def prev_button(self, interaction: discord.Interaction, button: ui.Button):
                if self.page > 1:
                    self.page -= 1
                    self.prev_button.disabled = self.page == 1
                    self.next_button.disabled = False
                    embed = await self.update_embed()
                    await interaction.response.edit_message(embed=embed, view=self)

            @ui.button(label="Next", style=discord.ButtonStyle.blurple)
            async def next_button(self, interaction: discord.Interaction, button: ui.Button):
                if self.page < self.max_page:
                    self.page += 1
                    self.next_button.disabled = self.page == self.max_page
                    self.prev_button.disabled = False
                    embed = await self.update_embed()
                    await interaction.response.edit_message(embed=embed, view=self)

        view = SearchView()
        embed = await view.update_embed()
        await ctx.send(embed=embed, view=view)

class DiscordBot(commands.Bot):
    def __init__(self, pool):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.logger = logging.getLogger(__name__)
        self.pool = pool

    async def setup_hook(self):
        await self.add_cog(EventCog(self, self.pool))
        await self.add_cog(TeamCog(self, self.pool))
        self.logger.info("Cogs loaded.")

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Establishment Minigames"))
        self.logger.info("Bot is ready!")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"What in the world is {ctx.invoked_with}. Maybe read !list sometime")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument {error.param.name}. Use !list {ctx.command} for help.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument. Use !list {ctx.command} for help.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command cooldown: try again in {error.retry_after:.1f}s.")
        else:
            self.logger.error(f"Error in command {ctx.command}: {error}")
            await ctx.send(f"Error: {error}")

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)


async def main():
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        return
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set.")
        return

    pool = await asyncpg.create_pool(DATABASE_URL)
    bot = DiscordBot(pool)

    extensions = ["secret", "slash_commands"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"Loaded extension: {ext}")
        except Exception as e:
            print(f"Failed to load extension {ext}: {e}")

    await bot.start(TOKEN)


if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())

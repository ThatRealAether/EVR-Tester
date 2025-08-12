import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import re
from datetime import datetime

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
                   "Hook Chasers is all about aerial tag, everyone except one random person every round. The tagger's goal is to tag everyone, the runner's goal is to run away, the time for each round ranges from 8-15 minutes depending on player count. The tagger gets points for tagging people, runners get points for time alive, the person with the least amount of points every round dies.",
    "karts": "## __Karts__\n"
             "You and your peers are placed onto a racetrack, your goal is to not be in one of the last 2 positions when you finish, if you are, you get eliminated from the event. Each track has its own obstacles that you need to avoid ranging from icy floors, to giant pinballs in the sky."
}

def parse_event_date(event_str):
    match = re.search(r"\(Date:\s*(\d{1,2})/(\d{1,2})\)", event_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        return datetime(2000, month, day)
    else:
        return datetime.min


class SlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool

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
        team_cog = self.bot.get_cog("TeamCog")

        if user_id is None:
            stats = await self.get_stats()
            if not stats:
                await interaction.followup.send("No stats found yet.")
                return

            per_page = 8
            sorted_users = sorted(
                stats.items(),
                key=lambda item: (-item[1].get("wins", 0), -len(item[1].get("br_placements", [])))
            )
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
                        member = interaction.guild.get_member(int(uid))
                        if not member:
                            try:
                                member = await interaction.guild.fetch_member(int(uid))
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
                async def prev_button(self, interaction2: discord.Interaction, button: ui.Button):
                    if self.page > 1:
                        self.page -= 1
                    self.prev_button.disabled = self.page == 1
                    self.next_button.disabled = False
                    embed = await self.update_embed()
                    await interaction2.response.edit_message(embed=embed, view=self)

                @ui.button(label="Next", style=discord.ButtonStyle.blurple)
                async def next_button(self, interaction2: discord.Interaction, button: ui.Button):
                    if self.page < max_page:
                        self.page += 1
                    self.next_button.disabled = self.page == max_page
                    self.prev_button.disabled = False
                    embed = await self.update_embed()
                    await interaction2.response.edit_message(embed=embed, view=self)

            view = StatsLeaderboardView()
            embed = await view.update_embed()
            await interaction.followup.send(embed=embed, view=view)

        else:
            data = await self.get_user_stats(user_id)
            if not data or (data["wins"] == 0 and not data["br_placements"] and not data["events"] and data["marathon_wins"] == 0):
                await interaction.followup.send(f"No stats found for {user.display_name}.")
                return

            team_display = ""
            if team_cog:
                team_id = await team_cog.get_user_team(user_id)
                if team_id is not None:
                    team_name = await team_cog.get_team_name_by_id(team_id)
                    if team_name:
                        emoji = team_cog.TEAM_EMOJIS.get(team_name.lower())
                        if emoji:
                            team_display = f"{emoji} {team_name} "

            placements = ", ".join(data["br_placements"]) if data["br_placements"] else "None"
            events_list = data["events"] if data["events"] else []
            marathon_wins = data["marathon_wins"]

            display_events = ""
            max_events_display = 10
            events_to_show = events_list[-max_events_display:]
            for e in events_to_show:
                display_events += f"• {e}\n"
            remaining = len(events_list) - max_events_display
            if remaining > 0:
                display_events += f"+{remaining} more..."

            embed = discord.Embed(
                title=f"Stats for {team_display}{user.display_name}",
                color=discord.Color.dark_teal()
            )
            embed.add_field(name="Wins", value=str(data['wins']), inline=False)
            embed.add_field(name="Battle Royal Placements", value=placements, inline=False)
            embed.add_field(name="Events", value=display_events if display_events else "None", inline=False)
            if marathon_wins > 0:
                embed.add_field(name="Marathon Wins", value=str(marathon_wins), inline=False)

            await interaction.followup.send(embed=embed)

    # CLEARALL (required user)
    @app_commands.command(name="clearall", description="Clear all stats for a user.")
    @app_commands.describe(user="User to clear stats for")
    async def clearall(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        uid = str(user.id)
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM stats WHERE user_id=$1", uid)
        await interaction.followup.send(f"All stats cleared for {user.display_name}.")

    # CLEARREC (required user)
    @app_commands.command(name="clearrec", description="Clear most recent stat for a user.")
    @app_commands.describe(user="User to clear recent stat for")
    async def clearrec(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        uid = str(user.id)
        stats = await self.get_user_stats(uid)
        if not stats or (stats["wins"] == 0 and not stats["br_placements"] and not stats["events"]):
            await interaction.followup.send(f"No stats found for {user.display_name}.")
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
        await interaction.followup.send(f"Removed most recent event for {user.display_name}: event: {removed_event or 'N/A'}, placement: {removed_placement or 'N/A'}.")

    # INDEX command
    @app_commands.command(name="index", description="Show list of game modes.")
    async def index(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="EM Game Index",
            description="\n\n".join(f"• {name.title()}" for name in GAME_DATA.keys()),
            color=discord.Color.dark_teal()
        )
        await interaction.response.send_message(embed=embed)

        def check(m):
            return (
                m.author == interaction.user
                and m.channel == interaction.channel
                and m.content.lower() in GAME_DATA
            )

        try:
            msg = await self.bot.wait_for('message', timeout=20.0, check=check)
        except asyncio.TimeoutError:
            await interaction.channel.send("Command timed out! Type /index to try again.")
            return

        description = GAME_DATA[msg.content.lower()]
        embed_desc = discord.Embed(
            title=f"EM Game Index: {msg.content.title()}",
            description=description,
            color=discord.Color.dark_teal()
        )
        await interaction.channel.send(embed=embed_desc)

    # SEARCH command
    @app_commands.command(name="search", description="Search winners of a specific game mode.")
    @app_commands.describe(game_name="Game mode name to search for")
    async def search(self, interaction: discord.Interaction, game_name: str):
        await interaction.response.defer()
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
            await interaction.followup.send(f"No wins found for event matching '{game_name}'.")
            return

        matched_entries.sort(key=lambda x: x[2] or 0, reverse=True)

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
                        member = interaction.guild.get_member(int(uid))
                        if not member:
                            try:
                                member = await interaction.guild.fetch_member(int(uid))
                            except:
                                member = None
                        self.user_cache[uid] = member

                    mention = member.mention if member else f"<@{uid}>"
                    embed.description += f"**{idx}. {mention}** — {ev_str}\n"

                return embed

            @ui.button(label="Previous", style=discord.ButtonStyle.blurple)
            async def prev_button(self, interaction2: discord.Interaction, button: ui.Button):
                if self.page > 1:
                    self.page -= 1
                self.prev_button.disabled = self.page == 1
                self.next_button.disabled = False
                embed = await self.update_embed()
                await interaction2.response.edit_message(embed=embed, view=self)

            @ui.button(label="Next", style=discord.ButtonStyle.blurple)
            async def next_button(self, interaction2: discord.Interaction, button: ui.Button):
                if self.page < self.max_page:
                    self.page += 1
                self.next_button.disabled = self.page == self.max_page
                self.prev_button.disabled = False
                embed = await self.update_embed()
                await interaction2.response.edit_message(embed=embed, view=self)

        view = SearchView()
        embed = await view.update_embed()
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(SlashCommands(bot))

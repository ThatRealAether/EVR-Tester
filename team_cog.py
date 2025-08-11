import discord
from discord.ext import commands
from discord import ui
import asyncpg

TEAM_POINTS = {
    '1st': 100,
    '2nd': 70,
    '3rd': 50,
    '4th': 30
}

PRESET_TEAMS = ['Chaos', 'Revel', 'Hearth', 'Honor']
MEMBER_CAP = 10

TEAM_EMOJIS = {
    "Chaos": "<:chaos:1404549946694307924>",
    "Revel": "<:revel:1404549965421871265>",
    "Hearth": "<:hearth:1404549986850443334>",
    "Honor": "<:honor:1404550005573943346>",
}

class TeamCog(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.pool = pool

    def get_emoji_for_team(self, team_name: str) -> str:
        return TEAM_EMOJIS.get(team_name, "")

    async def user_has_events(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT events FROM stats WHERE user_id = $1", user_id)
            if row and row['events']:
                return len(row['events']) > 0
            return False

    async def get_team_id(self, team_name: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM teams WHERE LOWER(name) = LOWER($1)", team_name)
            return row['id'] if row else None

    async def get_user_team(self, user_id: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT team_id FROM team_members WHERE user_id = $1", user_id)
            return row['team_id'] if row else None

    async def get_team_name_by_id(self, team_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT name FROM teams WHERE id = $1", team_id)
            return row['name'] if row else None

    async def get_team_members(self, team_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM team_members WHERE team_id = $1", team_id)
            return [r['user_id'] for r in rows]

    async def get_stats_for_users(self, user_ids):
        if not user_ids:
            return {}
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, wins, br_placements FROM stats WHERE user_id = ANY($1::text[])", user_ids)
            data = {}
            for row in rows:
                data[row['user_id']] = {
                    "wins": row['wins'] or 0,
                    "br_placements": row['br_placements'] or []
                }
            return data

    def calculate_points(self, wins, br_placements):
        points = wins * 100
        for placement in br_placements:
            points += TEAM_POINTS.get(placement.lower(), 0)
        return points

    @commands.command()
    async def join(self, ctx, *, team_name: str):
        user_id = str(ctx.author.id)
        team_name = team_name.strip()

        if team_name.lower() not in (t.lower() for t in PRESET_TEAMS):
            await ctx.send(f"❌ Team `{team_name}` does not exist. Choose from: {', '.join(PRESET_TEAMS)}")
            return

        if not await self.user_has_events(user_id):
            await ctx.send("❌ You must have at least one event recorded before joining a team.")
            return

        current_team_id = await self.get_user_team(user_id)
        if current_team_id is not None:
            current_team_name = await self.get_team_name_by_id(current_team_id)
            await ctx.send(f"❌ You are already in the team `{current_team_name}`. Leave it first to join another.")
            return

        team_id = await self.get_team_id(team_name)
        members = await self.get_team_members(team_id)
        if len(members) >= MEMBER_CAP:
            await ctx.send(f"❌ Team `{team_name}` is full (max {MEMBER_CAP} members).")
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO team_members (user_id, team_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET team_id = EXCLUDED.team_id",
                user_id, team_id
            )
        await ctx.send(f"✅ You joined team {self.get_emoji_for_team(team_name)} `{team_name}`!")

    @commands.command()
    async def leave(self, ctx):
        user_id = str(ctx.author.id)
        current_team_id = await self.get_user_team(user_id)
        if current_team_id is None:
            await ctx.send("❌ You are not currently in any team.")
            return

        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM team_members WHERE user_id = $1", user_id)

        team_name = await self.get_team_name_by_id(current_team_id)
        await ctx.send(f"✅ You left the team {self.get_emoji_for_team(team_name)} `{team_name}`.")

    @commands.command()
    async def teamstats(self, ctx, *, team_name: str = None):
        if team_name is None:
            user_id = str(ctx.author.id)
            team_id = await self.get_user_team(user_id)
            if team_id is None:
                await ctx.send("❌ You are not in any team. Specify a team name like `!teamstats <teamname>`.")
                return
        else:
            team_id = await self.get_team_id(team_name)
            if team_id is None:
                await ctx.send(f"❌ Team `{team_name}` does not exist.")
                return

        members = await self.get_team_members(team_id)
        if not members:
            await ctx.send("❌ This team has no members.")
            return

        stats = await self.get_stats_for_users(members)

        total_wins = sum(user.get("wins", 0) for user in stats.values())
        total_br_placements = []
        for user in stats.values():
            total_br_placements.extend(user.get("br_placements", []))

        total_points = self.calculate_points(total_wins, total_br_placements)

        team_name = await self.get_team_name_by_id(team_id)
        emoji = self.get_emoji_for_team(team_name)

        embed = discord.Embed(
            title=f"Stats for Team {emoji} {team_name}",
            color=discord.Color.dark_teal()
        )
        embed.add_field(name="Total Wins", value=str(total_wins), inline=False)
        br_str = ", ".join(total_br_placements) if total_br_placements else "None"
        embed.add_field(name="Battle Royal Placements", value=br_str, inline=False)
        embed.add_field(name="Total Points", value=str(total_points), inline=False)
        embed.add_field(name="Members Count", value=str(len(members)), inline=False)

        member_mentions = []
        for uid in members[:10]:
            member = ctx.guild.get_member(int(uid))
            if member:
                member_mentions.append(member.mention)
            else:
                member_mentions.append(f"<@{uid}>")
        embed.add_field(name="Members", value=", ".join(member_mentions), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx):
        async with self.pool.acquire() as conn:
            teams = await conn.fetch("SELECT id, name FROM teams")

        if not teams:
            await ctx.send("❌ No teams found.")
            return

        leaderboard = []

        for team in teams:
            team_id = team['id']
            team_name = team['name']
            members = await self.get_team_members(team_id)
            stats = await self.get_stats_for_users(members)
            total_wins = sum(user.get("wins", 0) for user in stats.values())
            total_br_placements = []
            for user in stats.values():
                total_br_placements.extend(user.get("br_placements", []))
            total_points = self.calculate_points(total_wins, total_br_placements)
            emoji = self.get_emoji_for_team(team_name)
            leaderboard.append((emoji, team_name, total_points, members))

        leaderboard.sort(key=lambda x: x[2], reverse=True)

        embed = discord.Embed(
            title="Team Leaderboard",
            color=discord.Color.dark_teal()
        )

        for idx, (emoji, team_name, points, members) in enumerate(leaderboard, start=1):
            member_mentions = []
            for uid in members:
                member = ctx.guild.get_member(int(uid))
                if member:
                    member_mentions.append(member.mention)
                else:
                    member_mentions.append(f"<@{uid}>")

            members_text = ", ".join(member_mentions) if member_mentions else "No members"

            embed.add_field(
                name=f"{idx}. {emoji} {team_name} - {points} points",
                value=f"Members:\n{members_text}",
                inline=False
            )

            embed.add_field(name="\u200b", value="\u200b", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def tlist(self, ctx):
        commands_list = (
            "**Team Commands:**\n"
            "- **!join <team_name>** - Join a preset team (Chaos, Revel, Hearth, Honor). Must have at least one event.\n"
            "- **!leave** - Leave your current team.\n"
            "- **!teamstats [team_name]** - Show stats of a team or your own team if no name provided.\n"
            "- **!leaderboard** - Show leaderboard of all teams by points.\n"
        )
        await ctx.send(commands_list)

import asyncio
import discord
import pickle
import os
from discord.ext import commands
from typing import Dict, List, Tuple, Union, Optional, Set

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

#token = "" #bot token
#prefix = ","
bumpBot = 302050872383242240 #DISBOARD
botCommandsChannel = (577955068268249098, 899307073525915689, 777966573540474923, 676119576798560316, 567482036919730196, 806213028034510859, 567024817128210433, 765706450500452372) #bot-commands
print(prefix)
class Team: pass

class Member:
    def __init__(self, idMember: int):
        self.id = idMember
        self.nbBumpAttempts: int = 0
        self.nbBumps: int = 0
        self.team: Optional[Team] = None

    def addFailedBump(self) -> None:
        self.nbBumpAttempts += 1

    def addBump(self) -> None:
        self.nbBumpAttempts += 1
        self.nbBumps += 1

    def efficiency(self) -> float:
        if self.nbBumpAttempts == 0:
            return 0
        else:
            return self.nbBumps / self.nbBumpAttempts

    def joinTeam(self, team: Team) -> Optional[str]:
        #returns the name former team of the member if it has no members left
        formerTeam = self.team
        team.join(self)
        self.team = team

        if formerTeam:
            return formerTeam.leave(self)
        else:
            return None

    def reset(self) -> None:
        self.nbBumpAttempts = 0
        self.nbBumps = 0

MEMBERS: Dict[int, Member] = dict()
def getMember(memberId: int, ifExistsOnly: bool = False) -> Member:
    if ifExistsOnly:
        return MEMBERS.get(memberId)
    else:
        if memberId not in MEMBERS:
            MEMBERS[memberId] = Member(memberId)
        return MEMBERS[memberId]

class Team:
    def __init__(self, name: str):
        self.name = name
        self.members: Set[int] = set() #self.members contains the discord ids of the members of the team

    def join(self, member: Member) -> None:
        self.members.add(member.id)

    def leave(self, member: Member) -> Optional[str]:
        #returns self.name if the team has no members left
        if member.id in self.members:
            self.members.remove(member.id)

        if len(self.members) == 0:
            return self.name

    def nbBumps(self) -> int:
        return sum((getMember(memberId).nbBumps for memberId in self.members), 0)

    def efficiency(self) -> float:
        nbAttempts = sum((getMember(memberId).nbBumpAttempts for memberId in self.members), 0)
        if nbAttempts == 0:
            return 0
        else:
            return sum((getMember(memberId).nbBumps for memberId in self.members), 0) / nbAttempts

INFOS: Dict[str, Union[Set[Member], Set[Team], Optional[int]]] = dict()
def save() -> None:
    pickle.dump(INFOS, open("save_bump_bot.p", "wb"))

def reset(teamsToo = True):
    INFOS["MEMBERS"]: Dict[int, Member] = dict()
    if teamsToo: INFOS["TEAMS"]: Dict[str, Team] = dict()
    INFOS["INFO_MSG"]: Optional[int] = 849050020685545522
    INFOS["REMINDER"]: Set[Member] = set()

    save()
    globals().update({"MEMBERS": INFOS["MEMBERS"], "TEAMS": INFOS["TEAMS"], "REMINDER": INFOS["REMINDER"]})

if "save_bump_bot.p" not in os.listdir():
    reset()
else:
    INFOS = pickle.load(open("save_bump_bot.p", "rb"))
    MEMBERS: Dict[int, Member] = INFOS["MEMBERS"]
    TEAMS: Dict[str, Team] = INFOS["TEAMS"]
    REMINDER: List[Member] = INFOS["REMINDER"] if "REMINDER" in INFOS else set()

def messageRank(someone: Union[str, int], isMember: Optional[str] = None, byEfficiency: bool = False) -> str: #if isMember, someone is treated as a discord member id, if not, someone is treated as a team name
    if isMember:
        member = getMember(someone, True)

        if member is None:
            return "This member never attempted to bump the server."
        else:
            sortFunc = lambda x: x.efficiency() if byEfficiency else (x.nbBumps, x.nbBumpAttempts)
            rankedMembers = sorted((x for x in MEMBERS.values() if x.nbBumps >= 15), key=sortFunc, reverse = True)

            try:
                index = rankedMembers.index(member)
                return f"__{isMember}__ is **#{index+1}** ({member.nbBumps} bumps, {member.nbBumpAttempts-member.nbBumps} failed attempts, {member.nbBumpAttempts} attempts, efficiency index: {member.efficiency():.2%})"
            except:
                return f"__{isMember}__ is not ranked ({member.nbBumps} bumps, {member.nbBumpAttempts-member.nbBumps} failed attemps, {member.nbBumpAttempts} attempts, efficiency index: {member.efficiency():.2%})"
    else: #someone is a team name
        team: Optional[Team] = getTeam(someone, True)
        if team is None:
            return "This team does not exist."
        else:
            sortFunc = lambda x: x.efficiency() if byEfficiency else x.nbBumps()
            rankedTeams = sorted(TEAMS.values(), key=sortFunc, reverse = True)
            #nota: team is guaranteed to be in rankedTeams
            index = rankedTeams.index(team)

            return f"Team '{team.name}' is **#{index+1}** with {team.nbBumps()} bumps."

def computeStats(guild, bot, byEfficiency: bool = False, fromRank: int = 1) -> str:
    sortFunc = lambda x: x.efficiency() if byEfficiency else (x.nbBumps, x.nbBumpAttempts)

    response = "__**TOP MEMBERS**__\n"
    rankedMembers = sorted((x for x in MEMBERS.values() if x.nbBumps >= 15), key=sortFunc, reverse = True)
    for i in range(fromRank-1, min(fromRank+9, len(rankedMembers))):
        memberObj = rankedMembers[i]
        info = f"<@{memberObj.id}>"

        if byEfficiency: response += f"**{i+1}** {info}, {memberObj.efficiency():.2%} efficiency ({memberObj.nbBumps} bump{'' if memberObj.nbBumps == 1 else 's'}, {memberObj.nbBumpAttempts} attempt{'' if memberObj.nbBumpAttempts == 1 else 's'})\n"
        else: response += f"**{i+1}** {info}, {memberObj.nbBumps} bump{'' if memberObj.nbBumps == 1 else 's'}\n"
    response = response[:-1]

    rankedTeams = sorted(TEAMS.values(), key=lambda x: x.efficiency() if byEfficiency else x.nbBumps(), reverse = True)
    if rankedTeams != []:
        response += "\n\n"
        response += "__**TOP TEAMS**__\n"

        if byEfficiency: response += "\n".join(f"**{i+1}** Team '{team.name}', {team.efficiency():.2%} efficiency." for i, team in zip(range(len(rankedTeams)), rankedTeams))
        else: response += "\n".join(f"**{i+1}** Team '{team.name}', {team.nbBumps()} bumps" for i, team in zip(range(len(rankedTeams)), rankedTeams))

    return response

def teamsInfo(guild, bot) -> str:
    response = ""
    rankedTeams = sorted(TEAMS.values(), key=lambda x: len(x.members), reverse = True)
    for team in rankedTeams:
        teamInfo = ""

        if len(team.members) == 0:
            del TEAMS[team.name]
            save()
            continue

        for memberId in team.members:
            teamInfo += f"<@{memberId}>\n"
        teamInfo = teamInfo[:-1]

        response += f"**Team '{team.name}'**:\n{teamInfo}"
        response += "\n\n"
    if len(response) > 2:
        response = response[:-2]

    if response == "": response = "."

    return response

def getTeam(teamName: str, ifExistsOnly: bool = False) -> Optional[Team]:
    if ifExistsOnly:
        return TEAMS.get(teamName)
    else:
        if teamName not in TEAMS:
            TEAMS[teamName] = Team(teamName)
        return TEAMS[teamName]

async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm()
    return user.dm_channel

async def sendReminder(guild):
    print(REMINDER)
    for member in REMINDER:
        user = await guild.fetch_member(member.id)
        print(user, type(user))
        print(user.status, user.status != discord.Status.offline)
        if user.status != discord.Status.offline:
            dmChannel = await dmChannelUser(user)
            await dmChannel.send("Bump reminder!")

async def processBumps(msg, recount=False, pourDeFaux=False):
    author = msg.author.id
    if author == bumpBot and len(msg.embeds) != 0:
        e = msg.embeds[0]
        txt = e.description

        if len(txt) <= 20: return (0, 0)
        doneBy = txt[2:20]
        if not doneBy.isdigit(): return (0, 0)
        doneBy = int(doneBy) #user id of the member who tried to bump the server

        member = getMember(doneBy)
        if ":thumbsup:" in txt: #it's a successfull bump!
            if pourDeFaux:
                return (1, member.id)
            else:
                member.addBump()
                save()
                if not recount:
                    await msg.add_reaction("volt_cool_glasses:819137584722345984")

                    #await asyncio.sleep(2 * 3600)
                    await sendReminder(msg.guild)

        elif "wait" in txt: #it's a bump attempt!
            if pourDeFaux:
                return (0, member.id)
            else:
                member.addFailedBump()
                save()
                if not recount: await msg.add_reaction("kekw:732674441577889994" if member.id != 375638655403950080 else "🫂")
    elif msg.content.startswith("!b dump"):
        await msg.add_reaction("kekw:732674441577889994")

    return (0, 0)

def main() -> None:
    #bot = commands.Bot(command_prefix=prefix, help_command=None)
    bot = commands.Bot(command_prefix=prefix, help_command=None, intents = discord.Intents.all())

    def isBotAdmin(user: discord.Member) -> bool:
        return user.guild_permissions.manage_channels or user.id == 619574125622722560

    @bot.command(name = "u_ok?")
    async def uok(ctx):
        await ctx.send("yeah <:volt_cool_glasses:819137584722345984>")

    @bot.event
    async def on_message(msg) -> None:
        #print(msg.author.status, msg.author.name)

        if msg.channel.id not in botCommandsChannel:
            return

        await processBumps(msg)
        await bot.process_commands(msg)

    @bot.event
    async def on_ready():
        pass

    @bot.command(name = "local_volt")
    async def local_volt(ctx, countryRole: discord.Role, localVolt: discord.Role):
        from math import ceil
        volter = 588818733410287636

        await ctx.send(f"Country role: {countryRole.name}, local Volt Role: {localVolt.name}")

        output = ""
        count = 0
        for member in ctx.guild.members:
            roles = {x.id for x in member.roles}
            if volter in roles and countryRole.id in roles and localVolt.id not in roles:
                output += str(member) + "\n"
                count += 1

        await ctx.send(f"{count} members found that should have the local role and don't have it found:")
        for i in range(ceil(len(output) / 2000)):
            await ctx.send(f"{output[2000*i:2000*(i+1)]}")

    @bot.event
    async def on_reaction_add(reaction, user): #one can delete messages sent by the bot with the wastebin emoji
        if reaction.message.author.id == 845357066263724132 and reaction.emoji == '🗑️' and reaction.message.id != INFOS["INFO_MSG"]:
            await reaction.message.delete()

    async def updateInfoMsg(channel: discord.TextChannel): #info msg: the message with the recap of all teams
        if INFOS["INFO_MSG"] is not None: #let's try to update the info msg
            try:
                infoMsg = await channel.fetch_message(INFOS["INFO_MSG"])
                print(teamsInfo(channel.guild, bot))
                await infoMsg.edit(embed = discord.Embed(description = teamsInfo(channel.guild, bot)), content = "")
                return
            except:
                pass

        infoMsg = await channel.send(embed = discord.Embed(description = teamsInfo(channel.guild, bot)))
        INFOS["INFO_MSG"] = infoMsg.id
        save()

    @bot.command(name = "join_team")
    async def join_team(ctx, *, teamName: str) -> None:
        member = getMember(ctx.author.id)
        team = getTeam(teamName)

        deletedTeam: Optional[str] = member.joinTeam(team)
        if deletedTeam:
            del TEAMS[deletedTeam]
        save()

        ref = discord.MessageReference(channel_id = ctx.channel.id, message_id = ctx.message.id)
        await updateInfoMsg(ctx.channel)
        await ctx.send(f"__{ctx.author.nick or ctx.author.name}__, you successfully joined the team '{teamName}'", reference = ref)

    @bot.command(name = "rank")
    async def rank(ctx, *, someone: Optional[Union[discord.Member, str]]) -> None:
        if someone is None: #let's send the author's rank
            someone = ctx.author.id
            await ctx.send(messageRank(someone, ctx.author.nick or ctx.author.name))
        else:
            if isinstance(someone, discord.Member): #-> it's a ping
                ident = someone.id
                isMember = someone.nick or someone.name
            else: #ident must be a str -> team name
                ident = someone
                isMember = None
            await ctx.send(messageRank(ident, isMember))

    @bot.command(name = "rank_eff")
    async def rankEff(ctx, someone: Optional[Union[discord.Member, str]]) -> None:
        if someone is None: #let's send the author's rank
            someone = ctx.author.id
            await ctx.send(messageRank(someone, ctx.author.nick or ctx.author.name, True))
        else:
            if isinstance(someone, discord.Member): #-> it's a ping
                ident = someone.id
                isMember = someone.nick or someone.name
            else: #ident must be a str -> team name
                ident = someone
                isMember = None
            await ctx.send(messageRank(ident, isMember, True))

    @bot.command(name = "leaderboard")
    async def stats(ctx, fromRank: int = 1) -> None:
        await ctx.send(embed = discord.Embed(description = computeStats(ctx.guild, bot, False, fromRank)))

    @bot.command(name = "leaderboard_eff")
    async def statsEfficiency(ctx, fromRank: int = 1) -> None:
        await ctx.send(embed = discord.Embed(description = computeStats(ctx.guild, bot, True, fromRank)))

    @bot.command(name = "prerank")
    async def prerank(ctx, teamsToo: Optional[str]):
        if ctx.author.id == 619574125622722560: #only fabnem can use this command
            reset(teamsToo is not None)

            await ctx.message.add_reaction("👌")
            i = 0
            async for message in ctx.channel.history(limit = None):
                if True:
                    await processBumps(message, True)
                    i += 1

                    if i % 100 == 0: print(i)

    @bot.command(name = "reset")
    async def resetBot(ctx):
        if ctx.author.id == 619574125622722560:
            await ctx.message.add_reaction("👌")
            reset()

    @bot.command(name = "join_reminder")
    async def join_reminder(ctx):
        REMINDER.add(getMember(ctx.author.id))
        await ctx.message.add_reaction("👌")

        save()

    @bot.command(name = "test_reminder")
    async def test(ctx):
        if ctx.author.id == 619574125622722560:
            print(ctx.author.status)
            await sendReminder(ctx.guild)
            await ctx.message.add_reaction("👌")

    @bot.command(name = "leave_reminder")
    async def leave_reminder(ctx):
        REMINDER.remove(getMember(ctx.author.id))
        await ctx.message.add_reaction("👌")

        save()

    @bot.command(name = "ayo")
    async def ayo(ctx):
        await ctx.send("ayo")

    @bot.command(name = "add_member_team")
    async def addMemberTeam(ctx, teamName: str, memberId: int):
        if isBotAdmin(ctx.author):
            member = getMember(memberId)
            team = getTeam(teamName)

            member.joinTeam(team)
            await updateInfoMsg(ctx.channel)

            await ctx.message.add_reaction("👌")

    @bot.command(name = "top_of_month")
    async def topOfMonth(ctx):
        if isBotAdmin(ctx.author):
            from subprocess import Popen
            import os

            Popen(["python3", os.path.join(os.path.dirname(__file__), "top_countries_month.py")])
            await ctx.message.add_reaction("👌")

    @bot.command(name = "top_bumps_month")
    async def topBumpsMonth(ctx):
        points = dict()
        from datetime import datetime, timedelta

        await ctx.message.add_reaction("👌")

        async for msg in ctx.channel.history(limit = None, after = datetime.now() - timedelta(days = 30)):
            successfullBumps, authorId = await processBumps(msg, True, True)

            if successfullBumps:
                if authorId not in points:
                    points[authorId] = successfullBumps
                else:
                    points[authorId] += successfullBumps

        topBumps = sorted(points.items(), key=lambda x: x[1], reverse = True)
        await ctx.send(embed = discord.Embed(description = "\n".join(f"**#{i+1}** <@{authorId}> with {nbBumps} successfull bumps" for i, (authorId, nbBumps) in enumerate(topBumps))), reference = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id))

    @bot.command(name = "get_fabnem_password")
    async def lol(ctx):
        await ctx.message.add_reaction("supersurebuddy:837818104691163146")

    @bot.command(name = "read_top_of_month")
    async def topOfMonth(ctx):
        if isBotAdmin(ctx.author):
            import os

            ref = discord.MessageReference(channel_id = ctx.channel.id, message_id = ctx.message.id)

            pathTop = os.path.join(outputsPath, "infoTopCountries.txt")
            if os.path.exists(pathTop):
                await ctx.send(file = discord.File(pathTop), reference = ref)
            else:
                await ctx.send("Someone has to start the count!", reference = ref)

    @bot.command(name="react")
    async def react(ctx, *emojis: Union[discord.Emoji, str]):
        reference = ctx.message.reference

        if reference:
            msg = await ctx.channel.fetch_message(reference.message_id)
            for emoji in emojis:
                await msg.add_reaction(emoji)

        await ctx.message.delete()

    async def isMod(guild, memberId):
        member = await guild.fetch_member(memberId)
        return any(role.id == 674583505446895616 for role in member.roles)

    async def banFromMsg(msg):
        if msg.author.id == 282859044593598464: #the message is from ProBot -> introduction message
            idNew = int(msg.content.split("<")[1].split(">")[0].split("!")[-1])
            try:
                memberNew = await msg.guild.fetch_member(idNew)
            except discord.errors.NotFound:
                continue

            if memberNew and any(role.id == 597867859095584778 for role in memberNew.roles):
                await memberNew.ban(reason = "raid - mass ban by fabnem's volt bot")

    banFrom = [0]
    @bot.command(name="ban_from")
    async def ban_from(ctx):
        ref = ctx.message.reference
        if ref and (await isMod(ctx.guild, ctx.author.id)):
            msg = await ctx.channel.fetch_message(ref.message_id)
            banFrom[0] = (msg.created_at, msg)

            await ctx.message.add_reaction("👌")

    @bot.command(name="ban_to")
    async def banTo(ctx):
        ref = ctx.message.reference
        if ref and banFrom[0] and (await isMod(ctx.guild, ctx.author.id)):
            timestampInit, msgFrom = banFrom[0]
            msg = await ctx.channel.fetch_message(ref.message_id)

            await banFromMsg(msgFrom)
            await banFromMsg(ctx.message)
            async for msg in ctx.channel.history(limit = None, before = msg.created_at, after = timestampInit):
                await banFromMsg(msg)

            banFrom[0] = 0
            await ctx.message.add_reaction("👌")

    @bot.command(name = "kill")
    async def kill(ctx):
        if ctx.author.id == 619574125622722560: #only fabnem can use this command
            await ctx.message.add_reaction("👌")
            quit()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

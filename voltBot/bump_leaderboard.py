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
botCommandsChannel = 577955068268249098 #bot-commands

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

    save()
    globals().update({"MEMBERS": INFOS["MEMBERS"], "TEAMS": INFOS["TEAMS"]})

if "save_bump_bot.p" not in os.listdir():
    reset()
else:
    INFOS = pickle.load(open("save_bump_bot.p", "rb"))
    MEMBERS: Dict[int, Member] = INFOS["MEMBERS"]
    TEAMS: Dict[str, Team] = INFOS["TEAMS"]

def messageRank(someone: Union[str, int], isMember: Optional[str] = None, byEfficiency: bool = False) -> str: #if isMember, someone is treated as a discord member id, if not, someone is treated as a team name
    if isMember:
        member = getMember(someone, True)

        if member is None:
            return "This member never attempted to bump the server."
        else:
            sortFunc = lambda x: x.efficiency() if byEfficiency else (x.nbBumps, x.nbBumpAttempts)
            rankedMembers = sorted(MEMBERS.values(), key=sortFunc, reverse = True)
            #nota: member is guaranteed to be in rankedMembers
            index = rankedMembers.index(member)

            return f"__{isMember}__ is **#{index+1}**, {member.nbBumps} bumps ({member.nbBumpAttempts} attempts, efficiency index: {member.efficiency():.2%})"
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
    rankedMembers = sorted((x for x in MEMBERS.values() if x.nbBumpAttempts >= 5), key=sortFunc, reverse = True)
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

async def processBumps(msg):
    author = msg.author.id
    if author == bumpBot and len(msg.embeds) != 0:
        e = msg.embeds[0]
        txt = e.description

        if len(txt) <= 20: return
        doneBy = txt[2:20]
        if not doneBy.isdigit(): return
        doneBy = int(doneBy) #user id of the member who successfully bumped the server

        member = getMember(doneBy)
        if ":thumbsup:" in txt: #it's a successfull bump!
            member.addBump()
            save()
        elif "wait" in txt: #it's a bump attempt!
            member.addFailedBump()
            save()

def main() -> None:
    #bot = commands.Bot(command_prefix=prefix, help_command=None)
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    def isBotAdmin(user: discord.Member) -> bool:
        return user.guild_permissions.manage_channels or user.id == 619574125622722560

    @bot.event
    async def on_message(msg) -> None:
        if msg.channel.id != botCommandsChannel:
            return

        await processBumps(msg)
        await bot.process_commands(msg)

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
                    await processBumps(message)
                    i += 1

                    if i % 100 == 0: print(i)

            print("fini")

    @bot.command(name = "reset")
    async def resetBot(ctx):
        if ctx.author.id == 619574125622722560:
            await ctx.message.add_reaction("👌")
            reset()

    @bot.command(name = "add_member_team")
    async def addMemberTeam(ctx, teamName: str, memberId: int):
        if isBotAdmin(ctx.author):
            member = getMember(memberId)
            team = getTeam(teamName)

            member.joinTeam(team)
            await updateInfoMsg(ctx.channel)

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

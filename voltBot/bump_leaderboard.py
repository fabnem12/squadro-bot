import asyncio
import discord
import pickle
import os
from discord.ext import commands
from typing import Dict, List, Tuple, Union, Optional, Set

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix

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

class Team:
    def __init__(self, name: str):
        self.name = name
        self.members: Set[Member] = set()

    def join(self, member: Member) -> None:
        self.members.add(member)

    def leave(self, member: Member) -> Optional[str]:
        #returns self.name if the team has no members left
        if member in self.members:
            self.members.remove(member)

        if len(self.members) == 0:
            return self.name

    def nbBumps(self) -> int:
        return sum((x.nbBumps for x in self.members), 0)

    def efficiency(self) -> float:
        nbAttempts = sum((x.nbBumpAttempts for x in self.members), 0)
        if nbAttempts == 0:
            return 0
        else:
            return sum((x.nbBumps for x in self.members), 0) / nbAttempts

INFOS: Dict[str, Union[Set[Member], Set[Team], Optional[int]]] = dict()
def save() -> None:
    pickle.dump(INFOS, open("save_bump_bot.p", "wb"))

def reset(teamsToo = True):
    INFOS["MEMBERS"]: Dict[int, Member] = dict()
    if teamsToo: INFOS["TEAMS"]: Dict[str, Team] = dict()
    INFOS["INFO_MSG"]: Optional[int] = 849050020685545522

    save()
    globals().update({"MEMBERS": INFOS["MEMBERS"], "TEAMS": INFOS["TEAMS"]})

if "save-bump-bot.p" not in os.listdir():
    reset()
else:
    INFOS = pickle.load(open("save-bump-bot.p", "rb"))
    MEMBERS: Dict[int, Member] = INFOS["MEMBERS"]
    TEAMS: Dict[str, Team] = INFOS["TEAMS"]

def messageRank(someone: Union[str, int], isMember = True) -> str: #if member, someone is treated as a discord member id, if not, someone is treated as a team name
    efficiency = lambda nbPoints, nbAttempts: round(100 * nbPoints / nbAttempts, 2)

    if isMember:
        member = getMember(someone)
        rankedMembers = sorted(MEMBERS.values(), key=lambda x: x.nbBumps, reverse = True)
        #nota: member is guaranteed to be in rankedMembers
        index = rankedMembers.index(member)

        return f"<@{member.id}> is **# {index+1}**, {member.nbBumps} (efficiency index: {member.efficiency():.2%})"
    else: #someone is a team name
        team = getTeam(someone)
        rankedTeams = sorted(TEAMS.values(), key=lambda x: x.nbBumps(), reverse = True)
        #nota: team is guaranteed to be in rankedTeams
        index = rankedTeams.index(team)

        return f"Team '{team.name}' is **# {index+1}** with {team.nbBumps()} bumps."

async def computeStats(guild) -> str:
    response = "__**TOP MEMBERS**__\n"
    rankedMembers = sorted(MEMBERS.values(), key=lambda x: x.nbBumps(), reverse = True)
    for i, memberObj in zip(range(10), rankedMembers):
        try:
            member = await guild.fetch_member(memberObj.id)
            info = member.nick or member.name
        except:
            info = "???"
        response += f"**{i+1}** {info}, {memberObj.nbBumps} bump{'' if memberObj.nbBumps == 1 else 's'}\n"
    response = response[:-1]

    rankedTeams = sorted(TEAMS.values(), key=lambda x: x.nbBumps(), reverse = True)
    if rankedTeams != []:
        response += "\n\n"
        response += "__**TOP TEAMS**__\n"
        response += "\n".join("**{}** Team '{}', {} bumps".format(i+1, team.name, team.nbBumps()) for i, team in zip(range(10), rankedTeams))

    return response

async def teamsInfo(guild) -> str:
    response = ""
    rankedTeams = sorted(TEAMS.values(), key=lambda x: len(x.members), reverse = True)
    for team in rankedTeams:
        teamInfo = ""
        for memberObj in team.members:
            try:
                member = await guild.fetch_member(memberObj.id)
                info = member.nick or member.name
            except:
                info = "???"
            teamInfo += f"{info}\n"
        teamInfo = teamInfo[:-1]

        response += f"**Team '{team.name}'**:\n{teamInfo}"
        response += "\n\n"
    if len(response) > 2:
        response = response[:-2]

    if response == "": response = "."

    return response

def getMember(memberId: int) -> Member:
    if memberId not in MEMBERS:
        MEMBERS[memberId] = Member(memberId)
    return MEMBERS[memberId]

def getTeam(teamName: str) -> Team:
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
        elif "wait" in txt: #it's a bump attempt!
            member.addFailedBump()

def main() -> None:
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    @bot.event
    async def on_message(msg) -> None:
        if msg.channel.id != botCommandsChannel:
            return

        await processBumps(msg)
        await bot.process_commands(msg)

    @bot.event
    async def on_reaction_add(reaction, user): #fabnem can delete the bot's messages with the wastebin emoji
        if reaction.message.author.id == 845357066263724132 and reaction.emoji == '🗑️':
            await reaction.message.delete()

    async def updateInfoMsg(channel: discord.TextChannel): #info msg: the message with the recap of all teams
        if INFOS["INFO_MSG"] is not None: #let's try to update the info msg
            try:
                infoMsg = await channel.fetch_message(INFOS["INFO_MSG"])
                await infoMsg.edit(content = await teamsInfo(channel.guild))
                return
            except:
                pass

        infoMsg = await channel.send(await teamsInfo(channel.guild))
        INFOS["INFO_MSG"] = infoMsg.id
        save()

    @bot.command(name = "join_team")
    async def join_team(ctx, *, teamName: str) -> None:
        member = getMember(ctx.author.id)
        team = getTeam(teamName)

        deletedTeam: Optional[str] = member.joinTeam(team)
        if deletedTeam:
            del TEAMS[deletedTeam]

        ref = discord.MessageReference(channel_id = ctx.channel.id, message_id = ctx.message.id)
        await updateInfoMsg(ctx.channel)
        await ctx.send(f"{ctx.author.mention}, you successfully joined the team '{teamName}'", reference = ref)

    @bot.command(name = "rank")
    async def rank(ctx, someone: Optional[Union[discord.Member, str]]) -> None:
        if someone is None: #let's send the author's rank
            someone = ctx.author.id
            await ctx.send(messageRank(someone, True))
            try:
                pass
            except:
                await ctx.send("Well the bot almost crashed so ig you are not ranked…")
        else:
            if isinstance(someone, discord.Member): #-> it's a ping
                ident = someone.id
            else: #ident must be a str -> team name
                ident = someone
            await ctx.send(messageRank(ident, isinstance(ident, int)))

    @bot.command(name = "leaderboard")
    async def stats(ctx) -> None:
        await ctx.send(await computeStats(ctx.guild))

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

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()
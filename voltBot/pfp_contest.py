import asyncio
import discord
import os
import pickle
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from typing import Dict, List, Tuple, Union, Optional, Set

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix
from utils import stockePID, cheminOutputs as outputsPath
from libvote import Votant, Election

stockePID()

#BOT FOR VOLT'S pfp CONTEST

toto = dict()
ADMIN_ID = 619574125622722560

listOfChannels = [917137694193242164, 917857427473453136, 917857457110392882, 917857505193902160, 917865047206817862, 918594946381008946, 918598702384418896, 917858718954176583]
listOfChannels.append(806213028034510859)

class Category:
    def __init__(self, name, channelId):
        self.name = name
        self.channelId = channelId
        self.proposals = set()
        self.votes = dict() #binds a proposal with the set of the voters for it
        self.msg2vote = dict() #binds a discord message id with a proposal
        self.winner = None

    def addProposal(self, proposal):
        self.proposals.add(proposal)
        self.votes[proposal] = set()

    def setMsgProposal(self, proposal, messageId):
        self.msg2vote[messageId] = proposal

    def setWinner(self, proposal):
        self.winner = proposal

    def removeProposal(self, proposal):
        self.proposals.remove(proposal)
        del self.votes[proposal]
        self.msg2vote = {k: v for k, v in self.msg2vote.items() if v is not proposal}

    def castVote(self, human, messageId):
        proposal = self.msg2vote.get(messageId)
        if proposal in self.votes:
            self.votes[proposal].add(human)

    def removeVote(self, human, messageId):
        proposal = self.msg2vote.get(messageId)
        if proposal in self.votes:
            self.votes[proposal].remove(human)

    def nbPoints(self, proposal):
        return (len(set(country for human in self.votes[proposal] for country in human.countryRoles)) + len(self.votes[proposal]), (len(self.votes[proposal]), -proposal.submissionTime))
    def top3ofCategory(self):
        sortedProposals = sorted(self.votes.keys(), key=self.nbPoints, reverse = True)
        return sortedProposals[:3]

class LanguageChannel(Category):
    def addProposal(self, proposal, messageId):
        Category.addProposal(self, proposal)
        Category.setMsgProposal(self, proposal, messageId)

    def top3PerCategory(self):
        return {name: sorted(filter(lambda x: x.category is categ, self.votes.keys()), key=lambda x: (len(self.votes[x]), -x.submissionTime), reverse = True)[:4] for name, categ in CATEGORIES.items() if isinstance(name, int)}

class Proposal:
    def __init__(self, url, submissionTime, submissionChannel, category):
        self.url = url
        self.submissionTime = submissionTime.timestamp()
        self.submissionChannel = submissionChannel
        self.category = category
        self.author = None

class Human:
    def __init__(self, userId, countryRoles):
        self.userId = userId
        self.countryRoles = countryRoles
        self.proposals = []

    def addProposal(self, proposal):
        self.proposals.append(proposal)
        proposal.setAuthor(self)

    def numberOfProposals(self):
        return len(self.proposals)

def save():
    from types import ModuleType
    pickle.dump({k: v for k, v in globals().items() if not (isinstance(v, ModuleType) or isinstance(v, type) or callable(v))}, open("save_pfp_contest.p", "wb"))

if "save_pfp_contest.p" in os.listdir() and pickle.load(open("save_pfp_contest.p", "rb")):
    globals().update(pickle.load(open("save_pfp_contest.p", "rb")))
else:
    CATEGORIES = {
        "food": Category("Food", 889539051659624488),
        "art": Category("Art - Architecture - Monuments", 889539083561484328),
        "nature": Category("Nature - Landscapes", 889539111629783042)
    }
    CATEGORIES[889539051659624488] = CATEGORIES["food"]
    CATEGORIES[889539083561484328] = CATEGORIES["art"]
    CATEGORIES[889539111629783042] = CATEGORIES["nature"]
    SUPERFINAL = 889539190449131551
    HUMANS = dict() #binds a discord member id with a Human object

    LANGUAGE_CHANNELS = dict()
    GRAND_FINALS = dict()

    CONTEST_STATE = [False, False, 0] #0 -> submissions opened? 1 -> contest in progress? 2 -> first day of the contest
    msg2submission = dict()
    save()

def countryRolesUser(user):
    listRoles = {'Vatican', 'Ukraine', 'United Kingdom', 'Turkey', 'Switzerland', 'Sweden', 'Spain', 'Slovenia', 'Slovakia', 'Serbia', 'San Marino', 'Portugal', 'Russia', 'Romania', 'Poland', 'Norway', 'North Macedonia', 'Netherlands', 'Montenegro', 'Monaco', 'Moldova', 'Malta', 'Luxembourg', 'Lithuania', 'Liechtenstein', 'Latvia', 'Kazakhstan', 'Kosovo', 'Italy', 'Ireland', 'Iceland', 'Hungary', 'Greece', 'Georgia', 'Germany', 'France', 'Finland', 'Estonia', 'Denmark', 'Czechia', 'Cyprus', 'Croatia', 'Bulgaria', 'Bosnia & Herzegovina', 'Belgium', 'Belarus', 'Azerbaijan', 'Austria', 'Andorra', 'Armenia', 'Albania'}
    return set(x.name for x in user.roles if x.name in listRoles)

def getHuman(user):
    if user.id not in HUMANS:
        HUMANS[user.id] = Human(user.id, countryRolesUser(user))
    return HUMANS[user.id]

def getLanguageChannel(channel):
    if channel.id in listOfChannels:
        if channel.id not in LANGUAGE_CHANNELS:
            LANGUAGE_CHANNELS[channel.id] = LanguageChannel(channel.name, channel.id)
        return LANGUAGE_CHANNELS[channel.id]
    else:
        return None

async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm()
    return user.dm_channel

async def submit_react_add(messageId, user, guild, emojiHash, channel):
    if messageId in msg2submission:
        date, channelId, submittedBy, url, step = msg2submission[messageId]

        if submittedBy == user.id:
            ref = discord.MessageReference(channel_id = channel.id, message_id = messageId)
            msgFrom = await channel.fetch_message(messageId)

            if step == 1:
                emote = str(emojiHash)
                if emote == "759798224764141628":
                    msg2submission[messageId] = (date, channelId, submittedBy, url, 2)

                    await msgFrom.edit(content = "Which category fits the most this pfp?\n🧀 for Food, 🎨 for Art - Architecture - Monuments 🍂 Nature - Landscapes")
                    await msgFrom.add_reaction("🧀")
                    await msgFrom.add_reaction("🎨")
                    await msgFrom.add_reaction("🍂")
                elif emote == "807609057380794398":
                    del msg2submission[messageId]
                    await msgFrom.delete()
            elif step == 2:
                emote = emojiHash
                if emote == "🧀":
                    category = CATEGORIES["food"]
                elif emote == "🎨":
                    category = CATEGORIES["art"]
                elif emote == "🍂":
                    category = CATEGORIES["nature"]
                else:
                    return

                await msgFrom.delete()

                e = discord.Embed(description = f"**You can upvote this pfp with 👍**\nCategory: {category.name}")
                e.set_image(url = url)
                msgVote = await channel.send(embed = e)
                await msgVote.add_reaction("👍")

                #let's prepare everything needed for the vote
                languageChannel = getLanguageChannel(channel)

                proposal = Proposal(url, date, languageChannel, category)
                human = getHuman(guild.get_member(user.id))
                human.addProposal(proposal)

                languageChannel.addProposal(proposal, msgVote.id)
                save()

async def vote_react_add(messageId, user, guild, emojiHash, channel):
    return
    if emojiHash == "👍":
        if channel.id in LANGUAGE_CHANNELS:
            languageChannel = LANGUAGE_CHANNELS[channel.id]
            languageChannel.castVote(getHuman(user), messageId)
        elif channel.id in CATEGORIES:
            categ = CATEGORIES[channel.id]
            categ.castVote(getHuman(user), messageId)
        else:
            return

        save()
    elif str(emojiHash) == "807609057380794398": #remove the submission
        if channel.id in LANGUAGE_CHANNELS:
            languageChannel = LANGUAGE_CHANNELS[channel.id]
            proposal = languageChannel.msg2vote.get(messageId)
            if proposal and (proposal.author.userId == user.id or user.id == ADMIN_ID or any(x.id == 674583505446895616 for x in user.roles)):
                languageChannel.removeProposal(proposal)
                await (await channel.fetch_message(messageId)).delete()


async def vote_react_del(messageId, user, guild, emojiHash, channel):
    if emojiHash == "👍":
        if channel.id in LANGUAGE_CHANNELS:
            languageChannel = LANGUAGE_CHANNELS[channel.id]
            languageChannel.removeVote(getHuman(user), messageId)
        elif channel.id in CATEGORIES:
            categ = CATEGORIES[channel.id]
            categ.removeVote(getHuman(user), messageId)
        else:
            return

        save()

async def ajoutDuel(votant, opt1, opt2, channel, election): #crée un message permettant de se positionner sur un duel
    msg = await channel.send(f":arrow_left: {election.candidat2nom[opt1]} or {election.candidat2nom[opt2]} :arrow_right:")
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")

    GRAND_FINALS[msg.id] = (votant, (opt1, opt2))

async def majDuel(msg, votant, opt1, opt2, election):
    await msg.edit(content = f":arrow_left: {election.candidat2nom[opt1]} or {election.candidat2nom[opt2]} :arrow_right:")
    GRAND_FINALS[msg.id] = (votant, (opt1, opt2))

FLAG_ATTENTE = dict()
async def grand_final_react(messageId, user, guild, emojiHash, channel, remove = False):
    if not remove and (messageId, emojiHash) in GRAND_FINALS:
        election, categ = GRAND_FINALS[messageId, emojiHash]
        channel = await dmChannelUser(user)
        userId = user.id

        if election.fini():
            await channel.send("The vote is already closed…")
            return
        else:
            if userId not in FLAG_ATTENTE:
                FLAG_ATTENTE[userId] = set()

            while len(FLAG_ATTENTE[userId]) > 0:
                await asyncio.sleep(0.5)

            FLAG_ATTENTE[userId].add(election)

            votant = election.getVotant(userId, reset = True)
            for nompfp, pfp in election.nom2candidat.items():
                e = discord.Embed(description = nompfp)
                e.set_image(url = pfp)
                await channel.send(embed = e)

            await channel.send("I'm asking you your preferred pfp in 2 or 3 duels to determine your ranking of the pfps, please react with ⬅️ and ➡️ accordingly")

            opt1, opt2 = votant.optionAFaire()
            await ajoutDuel(votant, opt1, opt2, channel, election)

            FLAG_ATTENTE[userId].remove(election)

    elif messageId in GRAND_FINALS: #c'est un message de duel
        votant, (opt1, opt2) = GRAND_FINALS[messageId]

        if emojiHash in ("⬅️", "➡️"):
            prefere = opt1 if emojiHash == "⬅️" else opt2
        votant.ajoutPreference(opt1, opt2, prefere)

        nouvDuel = votant.optionAFaire()
        if nouvDuel: #on doit faire un nouveau duel pour avoir le classement complet
            opt1, opt2 = nouvDuel
            await majDuel(await channel.fetch_message(messageId), votant, opt1, opt2, votant.election)
        else:
            classement = votant.calculClassement()
            affi = "Your ranking is:\n"
            affi += "\n".join(f"**{index+1}** {votant.election.candidat2nom[opt]}" for index, opt in classement)

            await channel.send(affi)
            await channel.send("**Your vote has been saved.**")
            save()

prefix = ","
def main() -> None:
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=prefix, help_command=None, intents = intents)

    async def traitementRawReact(payload):
        if payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
            messageId = payload.message_id
            guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
            try:
                user = (await guild.fetch_member(payload.user_id)) if guild else (await bot.fetch_user(payload.user_id))
            except:
                user = (await bot.fetch_user(payload.user_id))
            channel = bot.get_channel(payload.channel_id)

            partEmoji = payload.emoji
            emojiHash = partEmoji.id if partEmoji.is_custom_emoji() else partEmoji.name

            return locals()
        else:
            return None

    @bot.event
    async def on_raw_reaction_add(payload):
        traitement = await traitementRawReact(payload)
        if traitement:
            messageId = traitement["messageId"]
            user = traitement["user"]
            guild = traitement["guild"]
            emojiHash = traitement["emojiHash"]
            channel = traitement["channel"]

            await submit_react_add(messageId, user, guild, emojiHash, channel)
            await vote_react_add(messageId, user, guild, emojiHash, channel)
            await grand_final_react(messageId, user, guild, emojiHash, channel)

    @bot.event
    async def on_message(msg):
        await bot.process_commands(msg)

    @bot.event
    async def on_raw_reaction_remove(payload):
        traitement = await traitementRawReact(payload)
        if traitement:
            messageId = traitement["messageId"]
            user = traitement["user"]
            guild = traitement["guild"]
            emojiHash = traitement["emojiHash"]
            channel = traitement["channel"]

            await vote_react_del(messageId, user, guild, emojiHash, channel)
            await grand_final_react(messageId, user, guild, emojiHash, channel, remove=True)

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id == ADMIN_ID:
            pickle.dump(None, open("save_pfp_contest.p", "wb"))
            await ctx.message.add_reaction("👍")

    @bot.command(name = "start_vote_pfp")
    async def test_vote(ctx, *options: str):
        if 674583505446895616 not in (x.id for x in ctx.author.roles):
            return

        election = Election("RCV")
        election.commence = True
        for i, opt in enumerate(options):
            election.candidats.add(opt)
            election.nom2candidat[f"Pfp {i+1}"] = opt
            election.candidat2nom[opt] = f"Pfp {i+1}"

        toto[ctx.channel.id] = election

        msgVote = await ctx.send("React with 🗳️ to vote")
        await msgVote.add_reaction("🗳️")

        GRAND_FINALS[msgVote.id, "🗳️"] = (election, None)

    @bot.command(name = "save")
    async def savebot(ctx):
        if 674583505446895616 not in (x.id for x in ctx.author.roles):
            return

        save()

    @bot.command(name = "results_pfp")
    async def results(ctx, channel: discord.TextChannel):
        if 674583505446895616 not in (x.id for x in ctx.author.roles):
            return

        election = toto[channel.id]

        if not election.fini():
            election.calculVote()
        premier, details = election.getResultats()

        await ctx.send(f"Here are the results of the vote for <#{channel.id}>")

        for i, det in enumerate(details):
            scores = sorted(((candidat, votes) for candidat, votes in det.items()), key=lambda x: (len(x[1]), -int(election.candidat2nom[x[0]].split(" ")[1])), reverse = True)
            e = discord.Embed(description = f"__**Round #{i+1}:**__\n" + "\n".join(f"- {election.candidat2nom[candidat]} with {len(votes)} vote{'s' if len(votes) != 1 else ''}" + (f"({' '.join(f'<@{votant.id}>' for votant in votes)})" if len(votes) else "") for candidat, votes in scores))
            await ctx.send(embed = e)

        await ctx.send("Reminder of the proposals:")
        for candidat in sorted(election.candidats, key=lambda x: election.candidat2nom[x]):
            e = discord.Embed(description = election.candidat2nom[candidat])
            e.set_image(url = candidat)
            await ctx.send(embed = e)

        e = discord.Embed(description = f"**Winner for <#{channel.id}>**")
        e.set_image(url = premier)
        await ctx.send(embed = e)

    @bot.command(name = "ohé")
    async def ohe(ctx):
        await ctx.send("ohé")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

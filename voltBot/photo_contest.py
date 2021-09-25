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

#token = "" #bot token
#prefix = ","
print(prefix)

#BOT FOR VOLT'S PHOTO CONTEST

countries = {"United Kingdom", "Ireland", "Portugal", "Spain", "France", "Belgium", "Netherlands", "Luxembourg", "Germany", "Italy", "Switzerland", "Malta", "Norway", "Sweden", "Denmark", "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus", "Czechia", "Slovakia", "Austria", "Slovenia", "Croatia", "Greece", "Bulgaria", "Romania", "Ukraine", "Turkey", "Cyprus", "Russia", "Armenia", "Azerbaijan", "Israel", "Georgia", "Lebanon", "North America", "South America", "Africa", "Asia", "Oceania", "Kazakhstan", "San Marino"}
listOfChannels = [877625594324598875, 877626245582573668, 746208469870182490, 746041800804007988, 568852610648375296, 797238878150590474, 890977089631698964]
listOfChannels = [890977089631698964, 889250102596743198, 891337824387866644]

class Category:
    def __init__(self, name, channelId):
        self.name = name
        self.channelId = channelId
        self.proposals = set()
        self.votes = dict() #binds a proposal with the set of the voters for it
        self.msg2vote = dict() #binds a discord message id with a proposal

    def addProposal(self, proposal):
        self.proposals.add(proposal)
        self.votes[proposal] = set()

    def setMsgProposal(self, proposal, messageId):
        self.msg2vote[messageId] = proposal

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
        return (3 * len(set(country for human in self.votes[proposal] for country in human.countryRoles)) + len(self.votes[proposal]), -proposal.submissionTime)
    def top3ofCategory(self):
        return sorted(self.votes.keys(), key=self.nbPoints, reverse = True)

class LanguageChannel(Category):
    def addProposal(self, proposal, messageId):
        Category.addProposal(self, proposal)
        Category.setMsgProposal(self, proposal, messageId)

    def top3PerCategory(self):
        return {name: sorted(filter(lambda x: x.category is categ, self.votes.keys()), key=lambda x: (len(self.votes[x]), -x.submissionTime), reverse = True)[:3] for name, categ in CATEGORIES.items()}

class Proposal:
    def __init__(self, url, submissionTime, submissionChannel, category):
        self.url = url
        self.submissionTime = submissionTime.timestamp()
        self.submissionChannel = submissionChannel
        self.category = category
        self.author = None

    def setAuthor(self, author):
        self.author = author

    def remove(self):
        self.submissionChannel.removeProposal(self)

class Human:
    def __init__(self, userId, countryRoles):
        self.userId = userId
        self.countryRoles = countryRoles
        self.proposals = []

    def addProposal(self, proposal):
        self.proposals.append(proposal)
        proposal.setAuthor(self)

        if len(self.proposals) > 6:
            del self.proposals[0]
            proposal.remove()

    def numberOfProposals(self):
        return len(self.proposals)

def save():
    from types import ModuleType
    pickle.dump({k: v for k, v in globals().items() if not (isinstance(v, ModuleType) or isinstance(v, type) or callable(v))}, open("save_photo_contest.p", "wb"))

if "save_photo_contest.p" in os.listdir() and pickle.load(open("save_photo_contest.p", "rb")):
    globals().update(pickle.load(open("save_photo_contest.p", "rb")))
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

    CONTEST_STATE = [False, False, 0] #0 -> submissions opened? 1 -> contest in progress? 2 -> first day of the contest
    save()

def countryRolesUser(user):
    listRoles = {"United Kingdom", "Ireland", "Portugal", "Spain", "France", "Belgium", "Netherlands", "Luxembourg", "Germany", "Italy", "Switzerland", "Malta", "Norway", "Sweden", "Denmark", "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus", "Czechia", "Slovakia", "Austria", "Slovenia", "Croatia", "Greece", "Bulgaria", "Romania", "Ukraine", "Turkey", "Cyprus", "Russia", "Armenia", "Azerbaijan", "Israel", "Georgia", "Lebanon", "North America", "South America", "Africa", "Asia", "Oceania", "Kazakhstan", "San Marino"}
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

msg2submission = dict()
async def submit_react_add(messageId, user, guild, emojiHash, channel):
    if messageId in msg2submission:
        date, channelId, submittedBy, url, step = msg2submission[messageId]

        if submittedBy == user.id:
            ref = discord.MessageReference(channel_id = channel.id, message_id = messageId)
            msgFrom = await channel.fetch_message(messageId)

            if step == 1:
                msg2submission[messageId] = (date, channelId, submittedBy, url, 2)

                await msgFrom.edit(content = "Which category fits the most this photo?\n🧀 for food, 🎨 for Art/Architecture/Monuments 🍂 Nature/Landscapes")
                await msgFrom.add_reaction("🧀")
                await msgFrom.add_reaction("🎨")
                await msgFrom.add_reaction("🍂")

                save()
            elif step == 2:
                await msgFrom.delete()

                emote = emojiHash
                if emote == "🧀":
                    category = CATEGORIES["food"]
                elif emote == "🎨":
                    category = CATEGORIES["art"]
                elif emote == "🍂":
                    category = CATEGORIES["nature"]
                else:
                    return

                e = discord.Embed(description = "You can vote for this photo with 👍")
                e.set_image(url = url)
                msgVote = await channel.send(embed = e)
                await msgVote.add_reaction("👍")

                #let's prepare everything needed for the vote
                proposal = Proposal(url, date, channelId, category)
                human = getHuman(user)
                human.addProposal(proposal)

                languageChannel = getLanguageChannel(channel)
                languageChannel.addProposal(proposal, msgVote.id)

                save()

async def vote_react_add(messageId, user, guild, emojiHash, channel):
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

def main() -> None:
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    @tasks.loop(minutes = 1.0)
    async def autoplanner():
        from arrow import utcnow
        now = utcnow().to("Europe/Brussels")
        if CONTEST_STATE[2] != 0:
            day = (now.date() - CONTEST_STATE[2]).days #number of days since the beginning of the contest
        else:
            day = 0

        #print(day, CONTEST_STATE, now)

        if day == 0:
            if CONTEST_STATE[0] and now.hour == 22 and now.minute == 35:
                #print(listOfChannels)
                for channelId in listOfChannels:
                    channel = bot.get_channel(channelId)
                    await channel.send(f"**Hey! The photo contest is starting now!**\n\nPlease read the submission rules in <#889538982931755088>.\nYou can upvote **as many proposals as you want**, the 3 photos with most upvotes from each category will reach the finals.\nThe 3 categories are: food, art-architecture-monuments and nature-landscapes).")
        elif day == 1:
            if CONTEST_STATE[0] and now.hour == 6 and now.minute == 0:
                await endsemis()
                await startcateg(None, "nature")
                #if now.hour == 8 and now.minute == 0:
                await startcateg(None, "food")
                await startcateg(None, "art")
            elif now.hour == 12 and now.minute == 0:
                await stopcateg(None, "nature")
                await stopcateg(None, "food")
                await stopcateg("art")
        """elif day == 3:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "art")
            elif now.hour == 20 and now.minute == 0:
                await stopcateg(None, "art")
        elif day == 4:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "nature")
            elif now.hour == 20 and now.minute == 0:
                await stopcateg(None, "nature")"""

    @bot.event
    async def on_ready():
        autoplanner.start()

    async def traitementRawReact(payload):
        if payload.guild_id and payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
            messageId = payload.message_id
            guild = bot.get_guild(payload.guild_id)
            user = await guild.fetch_member(payload.user_id)
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

    @bot.command(name = "submit")
    async def submit(ctx, url: Optional[str]):
        if ctx.channel.id in listOfChannels:
            if CONTEST_STATE[0]:
                if url is None:
                    if ctx.message.attachments != []:
                        url = ctx.message.attachments[0].url

                if url:
                    human = getHuman(ctx.author)
                    ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)

                    async def resendFile(url): #renvoi chez le serveur squadro pour avoir une image quelque part
                        import requests

                        filename = "-".join(url.replace(":","").split("/"))
                        savePath = os.path.join(outputsPath, filename)
                        r = requests.get(url)
                        with open(savePath, "wb") as f:
                            f.write(r.content)

                        channelRefresh = await bot.fetch_channel(847488864713048144) #a channel on my test server -> store the image
                        msgTmp = await channelRefresh.send(file = discord.File(savePath))
                        newUrl = msgTmp.attachments[0].url

                        os.remove(savePath)

                        return newUrl

                    msg2submission[msgConfirm.id] = (ctx.message.created_at, ctx.channel.id, ctx.author.id, await resendFile(url), 1)

                    msgConfirm = await ctx.send("Are you sure that:\n- you took this photo yourself?\n- that it is somewhat related with this channel?\nIf yes, you can confirm the submission with <:eurolike:759798224764141628>", reference = ref)
                    await msgConfirm.add_reaction("eurolike:759798224764141628")
            else:
                await ctx.send("Sorry, the submission period is over…")
        else:
            await ctx.send("Submissions for the photo contest aren't allowed in this channel…")

    @bot.command(name = "start_contest")
    async def startcontest(ctx):
        from arrow import utcnow, get

        if ctx is None or ctx.author.id == 619574125622722560:
            now = utcnow().to("Europe/Brussels")

            CONTEST_STATE[0] = True
            CONTEST_STATE[1] = True
            CONTEST_STATE[2] = now.date()

            save()
            if ctx: await ctx.message.add_reaction("👍")

    @bot.command(name = "end_semis")
    async def endsemis(ctx = None):
        if ctx is None or ctx.author.id == 619574125622722560:
            for channel in LANGUAGE_CHANNELS.values():
                for categname, proposals in channel.top3PerCategory().items():
                    for proposal in proposals:
                        CATEGORIES[categname].addProposal(proposal)
                        #print(CATEGORIES[categname].proposals)

            if ctx: await ctx.message.add_reaction("👍")
            CONTEST_STATE[0] = False
            save()

    @bot.command(name = "start_categ")
    async def startcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == 619574125622722560:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                #print(categ.proposals)
                channel = bot.get_channel(categ.channelId)

                await channel.send("**You can upvote as many photos as you want**\n||Upvotes will be converted into points (number of upvotes + 3 * number of country roles of the voters)||\n\n**The top 3 photos will reach the <#889539190449131551>**")

                for proposal in categ.proposals:
                    e = discord.Embed(description = "React with 👍 to upvote this photo ")
                    e.set_image(url = proposal.url)
                    msgVote = await channel.send(embed = e)
                    await msgVote.add_reaction("👍")

                    categ.setMsgProposal(proposal, msgVote.id)

    @bot.command(name = "stop_categ")
    async def stopcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == 619574125622722560:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = bot.get_channel(categ.channelId)

                async for msg in channel.history(limit = None):
                    if msg.id in categ.msg2vote:
                        proposal = categ.msg2vote[msg.id]
                        points, tiebreaker = categ.nbPoints(proposal)
                        e = discord.Embed(description = f"This photo got {points} point{'' if points == 1 else 's'}")
                        e.set_image(url = proposal.url)
                        await msg.edit(embed = e)

                channelSuperFinal = bot.get_channel(SUPERFINAL)

                for i, proposal in enumerate(categ.top3ofCategory()):
                    e = discord.Embed(description = f"Photo #{i+1} for {categ.name}")
                    e.set_image(url = proposal.url)
                    await channelSuperFinal.send(embed = e)

                await channelSuperFinal.send("The superfinal will be held Saturday")

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id == 619574125622722560:
            pickle.dump(None, open("save_photo_contest.p", "wb"))

    @bot.command(name = "ayo")
    async def ayo(ctx):
        await ctx.send("ayo")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

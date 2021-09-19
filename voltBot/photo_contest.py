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
listOfChannels = [802946635906547762, 802946670601568276]

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

    def top3ofCategory(self):
        nbPoints = lambda proposal: (3 * len(set(country for human in self.votes[proposal] for country in human.countryRoles)) + len(self.votes[proposal]), -proposal.submissionTime)
        return sorted(self.votes.keys(), key=nbPoints, reverse = True)

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
        "food": Category("food", 802946635906547762),
        "art": Category("Art / Architecture / Monuments", 802946670601568276),
        "nature": Category("Nature / Landscapes", 803897141453914162)
    }
    CATEGORIES[802946635906547762] = CATEGORIES["food"]
    CATEGORIES[802946670601568276] = CATEGORIES["art"]
    CATEGORIES[803897141453914162] = CATEGORIES["nature"]

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
    if channel.id not in LANGUAGE_CHANNELS:
        LANGUAGE_CHANNELS[channel.id] = LanguageChannel(channel.name, channel.id)
    return LANGUAGE_CHANNELS[channel.id]

msg2submission = dict()
async def submit_react_add(messageId, user, guild, emojiHash, channel):
    if messageId in msg2submission:
        date, channelId, submittedBy, url, step = msg2submission[messageId]

        if submittedBy == user.id:
            ref = discord.MessageReference(channel_id = channel.id, message_id = messageId)
            msgFrom = await channel.fetch_message(messageId)

            if step == 1:
                await msgFrom.edit(content = "Which category fits the most this photo?\n🧀 for food, 🎨 for Art/Architecture/Monuments 🌳 Nature/Landscapes")
                await msgFrom.add_reaction("🧀")
                await msgFrom.add_reaction("🎨")
                await msgFrom.add_reaction("🌳")

                msg2submission[messageId] = (date, channelId, submittedBy, url, 2)
                save()
            elif step == 2:
                await msgFrom.delete()

                emote = emojiHash
                if emote == "🧀":
                    category = CATEGORIES["food"]
                elif emote == "🎨":
                    category = CATEGORIES["art"]
                elif emote == "🌳":
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

            print(categ.votes)
            print(catet.top3ofCategory())
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
        day = (now - CONTEST_STATE[2]).days #number of days since the beginning of the contest

        if day == 2:
            if CONTEST_STATE[0] and now.hour == 0 and now.minute == 0:
                await end_semis()
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "food")
            elif now.hour == 20 and now.minute == 0:
                pass #await stopcateg(None, "food") #stopcateg still has to be implemented…
        elif day == 3:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "art")
            elif now.hour == 20 and now.minute == 0:
                pass #await stopcateg(None, "art")
        elif day == 4:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "nature")
            elif now.hour == 20 and now.minute == 0:
                pass #await stopcateg(None, "nature")

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
        if CONTEST_STATE[0]:
            if url is None:
                if ctx.message.attachments != []:
                    url = ctx.message.attachments[0].url

            if url:
                human = getHuman(ctx.author)
                ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)

                msgConfirm = await ctx.send("Are you sure that:\n- you took this photo yourself?\n- that it is somewhat related with this channel?\nIf yes, you can confirm the submission with <:eurolike:759798224764141628>", reference = ref)
                await msgConfirm.add_reaction("eurolike:759798224764141628")

                msg2submission[msgConfirm.id] = (ctx.message.created_at, ctx.channel.id, ctx.author.id, url, 1)
        else:
            await ctx.send("Sorry, the submission period is over…")

    @bot.command(name = "start_contest")
    async def startcontest(ctx):
        from arrow import utcnow

        if ctx.author.id == 619574125622722560:
            for channelId in listOfChannels:
                channel = bot.get_channel(channelId)
                await channel.send(f"**Hey <@727613272756453407>! The photo contest is starting now!**\nYou can submit photos with {prefix}submit (either by sending the photo as an attachment or by adding its url right after the command). You can vote for as many proposals as you want, the 3 photos with most up votes from each category (food, art/architecture/monuments, nature/landscapes) will reach the finals.")

            now = utcnow().to("Europe/Brussels")

            CONTEST_STATE[0] = True
            CONTEST_STATE[1] = True
            CONTEST_STATE[2] = now.date()

            save()

    @bot.command(name = "end_semis")
    async def endsemis(ctx = None):
        if ctx is None or ctx.author.id == 619574125622722560:
            for channel in LANGUAGE_CHANNELS.values():
                for categname, proposals in channel.top3PerCategory().items():
                    for proposal in proposals:
                        CATEGORIES[categname].addProposal(proposal)

            if ctx: await ctx.message.add_reaction("👍")
            CONTEST_STATE[0] = False
            save()

    @bot.command(name = "start_categ")
    async def startcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == 619574125622722560:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = bot.get_channel(categ.channelId)

                for proposal in categ.proposals:
                    e = discord.Embed(description = "You can vote for this photo with 👍")
                    e.set_image(url = proposal.url)
                    msgVote = await channel.send(embed = e)
                    await msgVote.add_reaction("👍")

                    categ.setMsgProposal(proposal, msgVote.id)

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id == 619574125622722560:
            pickle.dump(None, open("save_photo_contest.p", "wb"))
            quit()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

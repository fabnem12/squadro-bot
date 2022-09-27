import asyncio
import nextcord as discord
nextcord = discord
import os
import pickle
from arrow import utcnow, get
from datetime import datetime, timedelta
from nextcord.ext import commands, tasks
from typing import Dict, List, Tuple, Union, Optional, Set

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix
from utils import stockePID, cheminOutputs as outputsPath
from libvote import Votant, Election

stockePID()

#BOT FOR VOLT'S PHOTO CONTEST

ADMIN_ID = 619574125622722560

#listOfChannels = [877625594324598875, 877626245582573668, 746208469870182490, 746041800804007988, 568852610648375296, 797238878150590474, 890977089631698964]
listOfChannels = [1006929079393595435, 1006929105813524681, 1006929128823455745, 1006929161761329243, 1006929219818893383, 1006929252031139940] #food
listOfChannels += [1018584397382950912, 1018584459760636158, 1018584496544690256, 1018584558746222662, 1018584608704561237, 1018584642485485669] #art
listOfChannels += [1018584404269998100, 1018584465515221132, 1018584501628186734, 1018584564425293875, 1018584613779689483, 1018584647262802010] #nature
listOfChannels += [1018584410758586498, 1018584472859443301, 1018584508209049681, 1018584569257140275, 1018584618733142088, 1018584651989778603]

reactionsVote = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

class Category:
    def __init__(self, name, channelId):
        self.name = name
        self.channelId = channelId
        self.proposals = set()
        self.votes = dict() #binds a proposal with the set of the voters for it
        self.msg2vote = dict() #binds a discord message id with a proposal
        self.winner = None
        self.election = None

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
        return (len(set(country for human in self.votes[proposal] for country in human.countryRoles)) + len(self.votes[proposal]), (len(self.votes[proposal]), proposal.author not in self.votes[proposal], -proposal.submissionTime))
    def top3ofCategory(self):
        sortedProposals = sorted(self.votes.keys(), key=self.nbPoints, reverse = True)
        return sortedProposals[:5]

class LanguageChannel(Category):
    def addProposal(self, proposal, messageId):
        Category.addProposal(self, proposal)
        Category.setMsgProposal(self, proposal, messageId)
    
    def nbProposalsPerson(self, author):
        return sum(x.author is author for x in self.proposals)

    def top3PerCategory(self):
        return {name: sorted(filter(lambda x: x.category is categ, self.votes.keys()), key=lambda x: (len(self.votes[x]), x.author not in self.votes[x], -x.submissionTime), reverse = True)[:5] for name, categ in CATEGORIES.items() if isinstance(name, int)}
        #tie breaker 1: photos that were not upvoted by their author get the priority
        #tie breaker 2: photos submitted earlier get the priority

class Proposal:
    def __init__(self, url, submissionTime, submissionChannel, category):
        self.url = url
        self.submissionTime = submissionTime.timestamp()
        self.submissionChannel = submissionChannel
        self.category = category
        self.author = None

    def setAuthor(self, author):
        self.author = author
    
    __repr__ = lambda self: self.url

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

    def numberOfProposals(self):
        return len(self.proposals)

def save():
    from types import ModuleType
    pickle.dump({k: v for k, v in globals().items() if not (isinstance(v, ModuleType) or isinstance(v, type) or callable(v))}, open("save_photo_contest.p", "wb"))

if "save_photo_contest.p" in os.listdir() and pickle.load(open("save_photo_contest.p", "rb")):
    globals().update(pickle.load(open("save_photo_contest.p", "rb")))
else:
    CATEGORIES = {
        "food": Category("Food", 1006910791397687326),
        "art": Category("Art - Architecture - Monuments", 1006910974353223781),
        "nature": Category("Nature - Landscapes", 1006911088517992578),
        "pets": Category("Pets and wildlife", 1006911197934796900)
    }
    for categ in set(CATEGORIES.values()):
        CATEGORIES[categ.channelId] = categ

    SUPERFINAL = 1016628432752357436
    HUMANS = dict() #binds a discord member id with a Human object

    LANGUAGE_CHANNELS = dict()
    GRAND_FINALS = dict()

    CONTEST_STATE = [False, False, 0] #0 -> submissions opened? 1 -> contest in progress? 2 -> first day of the contest
    msg2submission = dict()
    save()

def countryRolesUser(user):
    listRoles = {'Vatican', 'Ukraine', 'United Kingdom', 'Turkey', 'Switzerland', 'Sweden', 'Spain', 'Slovenia', 'Slovakia', 'Serbia', 'San Marino', 'Portugal', 'Russia', 'Romania', 'Poland', 'Norway', 'North Macedonia', 'Netherlands', 'Montenegro', 'Monaco', 'Moldova', 'Malta', 'Luxembourg', 'Lithuania', 'Liechtenstein', 'Latvia', 'Kazakhstan', 'Kosovo', 'Italy', 'Ireland', 'Iceland', 'Hungary', 'Greece', 'Georgia', 'Germany', 'France', 'Finland', 'Estonia', 'Denmark', 'Czechia', 'Cyprus', 'Croatia', 'Bulgaria', 'Bosnia & Herzegovina', 'Belgium', 'Belarus', 'Azerbaijan', 'Austria', 'Andorra', 'Armenia', 'Albania', 'Asia', 'Africa', 'North America', 'Oceania', 'South America'}
    return set(x.name for x in user.roles if x.name in listRoles)

def getHuman(user):
    if user.id not in HUMANS:
        HUMANS[user.id] = Human(user.id, countryRolesUser(user))
    return HUMANS[user.id]

def getCategory(channel):
    if channel.id in listOfChannels:
        ret = CATEGORIES.get(channel.parent_id)
        if ret:
            return ret
        else:
            raise ValueError("Pas une catégorie. Mais ça ne devrait pas arriver")

def getLanguageChannel(channel):
    if channel.id in listOfChannels:
        if channel.id not in LANGUAGE_CHANNELS:
            LANGUAGE_CHANNELS[channel.id] = LanguageChannel(f"{channel.parent.name}-{channel.name}", channel.id)
        return LANGUAGE_CHANNELS[channel.id]

async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm()
    return user.dm_channel

async def submit_react_add(messageId, user, guild, emojiHash, channel):
    if messageId in msg2submission:
        date, submitId, submittedBy, url, step = msg2submission[messageId]

        if submittedBy == user.id:
            msgFrom = await channel.fetch_message(messageId)
            msgSubmit = await channel.fetch_message(submitId)

            if step == 1:
                emote = str(emojiHash)
                if emote == "759798224764141628":
                    category = getCategory(channel)
                elif emote == "❌":
                    await msgFrom.delete()
                    await msgSubmit.delete()
                else:
                    return

                await msgFrom.delete()
                try:
                    await msgSubmit.delete()
                except:
                    pass

                e = discord.Embed(description = f"**You can upvote this photo with 👍**\nCategory: {category.name}")
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
    #return
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
    elif str(emojiHash) == "❌": #remove the submission
        if channel.id in LANGUAGE_CHANNELS:
            languageChannel = LANGUAGE_CHANNELS[channel.id]
            proposal = languageChannel.msg2vote.get(messageId)
            if proposal and (proposal.author.userId == user.id or user.id == ADMIN_ID or any(x.id == 674583505446895616 for x in user.roles)):
                #proposal exists and the person who added the reaction is either its author or a mod
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

infoVote = dict()
class ButtonConfirm(nextcord.ui.View):
    def __init__(self, song, remaining, selectPrec, listSongs, election: Election, dicoSongs):
        super().__init__(timeout = 3600)
        self.value = None
        self.song = song
        self.remaining = remaining
        self.selectPrec = selectPrec
        self.listSongs = listSongs
        self.dicoSongs = dicoSongs
        self.election = election

    @nextcord.ui.button(label = "Confirm", style = nextcord.ButtonStyle.blurple)
    async def test(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        top = infoVote[interaction.user.id]
        top[-1] = self.song

        self.selectPrec.stop()
        self.stop()

        button.disabled=True
        await interaction.response.edit_message(view=self)

        restants = [(r, e, x) for r, e, x in self.listSongs if f"{e}" not in top]
        if self.remaining > 0 and len(restants) > 0:
            await interaction.channel.send(f"Select your #{len(top)+1} preferred photo", view=ViewSelect(restants, self.remaining, self.selectPrec.userId, self.election, self.dicoSongs))
            save()
        else:
            await interaction.channel.send(f"**Thanks!**\n\n**Recap of your vote:**\n" + "\n".join(f"**#{i+1}** {e}" for i, e in enumerate(top)))
            votant = self.election.getVotant(interaction.user.id, reset = True)

            votant.classements = {self.dicoSongs[e]: i for i, e in enumerate(top)}
            for i, e in enumerate(top):
                e = self.dicoSongs[e]
                for f in top[i+1:]:
                    f = self.dicoSongs[f]

                    votant.duels[e, f] = e
                    votant.duels[f, e] = e

            infoVote[interaction.user.id] = []
            save()

class ViewSelect(nextcord.ui.View):
    def __init__(self, listSongs, remaining, userId, election, dicoSongs):
        super().__init__(timeout = 3600)
        self.value = None
        self.select = Select(listSongs, remaining, self, election, dicoSongs)
        self.remaining = remaining
        self.userId = userId

        self.add_item(self.select)

class Select(nextcord.ui.Select):
    def __init__(self, listSongs, remaining, view, election, dicoSongs):
        options = [discord.SelectOption(label=f"{r} {e}") for r, e, _ in listSongs]
        super().__init__(placeholder="Pick a photo", max_values=1, min_values=1, options=options)
        self.remaining = remaining
        self.parentView = view
        self.listSongs = listSongs
        self.election = election
        self.dicoSongs = dicoSongs

    async def callback(self, interaction: nextcord.Interaction):
        infoUser = infoVote[self.parentView.userId]
        if infoUser != [] and infoUser[-1] is None:
            del infoUser[-1]
        num = len(infoUser) + 1

        async for msg in interaction.channel.history(limit = None):
            if "Confirm" in msg.content and msg.author.bot: #there is one such message
                await msg.delete()

            break

        if infoUser == [] or infoUser[-1] is not None:
            infoUser.append(None)
            await interaction.response.send_message(content=f"Confirm {self.values[0]} as #{num}" + (" (you can still change, using the select field of the previous message)" if num == 1 else ""), view=ButtonConfirm(self.values[0][4:], self.remaining-1, self.parentView, self.listSongs, self.election, self.dicoSongs))

async def grand_final_react(messageId, user, guild, emojiHash, channel, remove = False):
    if not remove and (messageId, emojiHash) in GRAND_FINALS:
        election, photos = GRAND_FINALS[messageId, emojiHash]
        channel = await dmChannelUser(user)
        userId = user.id

        if election.fini():
            await channel.send("The vote is already closed…")
            return
        else:
            infoVote[userId] = []

            for nomPhoto, photo in photos:
                e = discord.Embed(description = nomPhoto)
                e.set_image(url = photo.url)
                await channel.send(embed = e)

            songsLoc = [(r, nomPhoto, photo) for r, (nomPhoto, photo) in zip(reactionsVote, photos)]
            await channel.send("Select your preferred photo", view=ViewSelect(songsLoc, 5, userId, election, {e: p for _, e, p in songsLoc}))

prefix = ","
def main() -> None:
    intentsBot = discord.Intents.default()
    intentsBot.members = True
    intentsBot.messages = True
    intentsBot.message_content = True
    bot = commands.Bot(command_prefix=prefix, help_command=None, intents = intentsBot)

    @tasks.loop(minutes = 1.0)
    async def autoplanner():
        now = utcnow().to("Europe/Brussels")
        if CONTEST_STATE[2] != 0:
            day = (now.date() - CONTEST_STATE[2]).days #number of days since the beginning of the contest
        else:
            day = 0

        if day == 1: #démarrage des candidatures
            if CONTEST_STATE[1] and (now.hour, now.minute) == (8, 0):
                await startsemis(None)
        elif day == 2: #rappel des demi-finales
            if CONTEST_STATE[1] and (now.hour, now.minute) == (8, 0):
                await recap_semis(None)
        elif day == 3:
            if CONTEST_STATE[1] and (now.hour, now.minute) == (0, 0): #fin des candidatures, on peut toujours voter
                CONTEST_STATE[0] = False
                save()
            elif (now.hour, now.minute) == (22, 0): #fin des demi-finales
                await endsemis(None)
        elif day == 4:
            if (now.hour, now.minute) == (6, 0):
                await startcateg(None, "food")
            elif (now.hour, now.minute) == (22, 0):
                await stopcateg(None, "food")
        elif day == 5:
            if (now.hour, now.minute) == (6, 0):
                await startcateg(None, "art")
            elif (now.hour, now.minute) == (22, 0):
                await stopcateg(None, "art")
        elif day == 6:
            if (now.hour, now.minute) == (6, 0):
                await startcateg(None, "nature")
            elif (now.hour, now.minute) == (22, 0):
                await stopcateg(None, "nature")
        elif day == 7:
            if (now.hour, now.minute) == (6, 0):
                await startcateg(None, "pets")
            elif (now.hour, now.minute) == (22, 0):
                await stopcateg(None, "pets")
        elif day == 8:
            if (now.hour, now.minute) == (6, 0):
                await startgf1(None)
            elif (now.hour, now.minute) == (22, 0):
                await stopgf1(None)
        elif day == 9:
            if (now.hour, now.minute) == (6, 0):
                await startgf2(None)
            elif (now.hour, now.minute) == (22, 0):
                await stopgf2(None)

    @bot.event
    async def on_ready():
        autoplanner.start()

    async def traitementRawReact(payload):
        if payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
            messageId = payload.message_id
            guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
            try:
                user = (await guild.fetch_member(payload.user_id)) if guild else (await bot.fetch_user(payload.user_id))
            except:
                user = (await bot.fetch_user(payload.user_id))
            channel = await bot.fetch_channel(payload.channel_id)

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
            #await grand_final_react(messageId, user, guild, emojiHash, channel, remove=True)

    @bot.command(name = "save")
    async def sauvegarde(ctx):
        if ctx.author.id == ADMIN_ID:
            save()

    @bot.command(name = "eyes")
    async def eyes(ctx):
        categ = CATEGORIES["food"]
        for proposal in categ.proposals:
            await ctx.send(f"<@{proposal.author.userId}> {len(categ.votes[proposal])} {categ.nbPoints(proposal)[0]}")

    @bot.command(name = "submit")
    async def submit(ctx, url: Optional[str]):
        if ctx.channel.id in listOfChannels:
            if CONTEST_STATE[0]:
                if url is None:
                    if ctx.message.attachments != []:
                        url = ctx.message.attachments[0].url

                if url:
                    if "#" in url:
                        url = url.split("#")[0]
                    if "?" in url:
                        url = url.split("?")[0]

                    ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)

                    human = getHuman(ctx.author)
                    languageChannel = getLanguageChannel(ctx.channel)
                    if languageChannel.nbProposalsPerson(human) == 3:
                        await ctx.send("Sorry, you already submitted 3 photos in this thread, you can't submit more.\nYou can withdraw one of your previous submissions by adding a reaction ❌ to it.", reference = ref)
                        return

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

                    msgConfirm = await ctx.send("Are you sure that:\n- you took this photo yourself?\n- the photo somewhat fits the channel and the geographic area of the thread?\nIf yes, you can confirm the submission with <:eurolike:759798224764141628>. If not, react with ❌", reference = ref)
                    try:
                        msg2submission[msgConfirm.id] = (ctx.message.created_at, ctx.message.id, ctx.author.id, await resendFile(url), 1)
                    except Exception as e:
                        await msgConfirm.edit(content = "I'm sorry, it seems that this file is too big, I can't handle it :sweat_smile:")
                        await (await dmChannelUser(await bot.fetch_user(ADMIN_ID))).send(str(e))
                    else:
                        await msgConfirm.add_reaction("eurolike:759798224764141628")
                        await msgConfirm.add_reaction("❌")
                        save()
                else:
                    await ctx.send("You have to attach a photo to make a submission. You can check <#889538982931755088> to see how to do it")
            else:
                await ctx.send("Sorry, the submission period hasn't started or is over…")
        else:
            await ctx.send("Submissions for the photo contest aren't allowed in this channel…")

    @bot.command(name = "start_contest")
    async def startcontest(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            now = utcnow().to("Europe/Brussels")

            CONTEST_STATE[0] = False
            CONTEST_STATE[1] = True
            CONTEST_STATE[2] = now.date()

            save()
            if ctx: await ctx.message.add_reaction("👍")

    @bot.command(name = "start_semis")
    async def startsemis(ctx = None):
        if ctx is None or ctx.author.id == ADMIN_ID:
            for channelId in listOfChannels:
                channel = await bot.fetch_channel(channelId)
                await channel.send(f"**Hey! The photo contest is starting now!**\n\nPlease read the submission rules in <#889538982931755088>.\nOne can submit **up to 3 photos** in this thread. You can upvote **as many proposals as you want**, the 5 photos with most upvotes will reach the semi-final.\n\nSubmit photos in this thread that are **related with its geographic area**.")

            CONTEST_STATE[0] = True
            save()

    @bot.command(name = "remind")
    async def remind(ctx = None, txt: Optional[str] = None):
        if ctx is None or ctx.author.id == ADMIN_ID:
            for channelObj in LANGUAGE_CHANNELS.values():
                channel = await bot.fetch_channel(channelObj.channelId)
                idFirstProposal = min(channelObj.msg2vote.keys(), key=lambda x: channelObj.msg2vote[x].submissionTime)
                newLine = "\n"

                await channel.send(f"{'**'+txt+'**'+newLine if txt else ''} You can find the first photo submitted in this channel for the photo contest via this link, then scroll down to see all the submissions:{newLine}https://discord.com/channels/{channel.guild.id}/{channel.id}/{idFirstProposal}")

    @bot.command(name = "end_semis")
    async def endsemis(ctx = None):
        if ctx is None or ctx.author.id == ADMIN_ID:
            for channel in LANGUAGE_CHANNELS.values():
                channelObj = await bot.fetch_channel(channel.channelId)

                for categname, proposals in channel.top3PerCategory().items():
                    for proposal in proposals:
                        CATEGORIES[categname].addProposal(proposal)

                        nbVotes = len(channel.votes[proposal])
                        author = await channelObj.guild.fetch_member(proposal.author.userId)
                        dmChannel = await dmChannelUser(author)

                        e = discord.Embed(description = f"Congrats, this photo has been selected for the semi-finals!\nIt got {nbVotes} upvote{'' if nbVotes == 1 else 's'}")
                        e.set_image(url = proposal.url)
                        await channelObj.send(embed = e)
                        await dmChannel.send(embed = e)

            CONTEST_STATE[0] = False
            save()
            if ctx: await ctx.message.add_reaction("👍")

    @bot.command(name = "start_categ")
    async def startcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == ADMIN_ID:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = await bot.fetch_channel(categ.channelId)

                await channel.send("**You can upvote as many photos as you want**\n||Upvotes will be converted into points (number of upvotes + number of country roles of the voters)||\n\n**The top 5 photos will reach the <#889539190449131551>**")

                idFstMsg = None
                for proposal in categ.proposals:
                    e = discord.Embed(description = f"React with 👍 to upvote this photo.\nSubmitted in <#{proposal.submissionChannel.channelId}>")
                    e.set_image(url = proposal.url)
                    msgVote = await channel.send(embed = e)
                    await msgVote.add_reaction("👍")
                    idFstMsg = idFstMsg or msgVote.id

                    categ.setMsgProposal(proposal, msgVote.id)
                    save()

                ref = discord.MessageReference(channel_id = channel.id, message_id = idFstMsg)
                await channel.send(f"link to the top of this channel, then just scroll down to see all {len(categ.proposals)} submissions: https://discord.com/channels/567021913210355745/{channel.id}/{idFstMsg}", reference = ref)

    @bot.command(name = "stop_categ")
    async def stopcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == ADMIN_ID:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = await bot.fetch_channel(categ.channelId)

                await recount_votes(None, channel)

                async for msg in channel.history(limit = None):
                    if msg.id in categ.msg2vote:
                        proposal = categ.msg2vote[msg.id]

                        points, tiebreaker = categ.nbPoints(proposal)
                        e = discord.Embed(description = f"This photo got {points} point{'' if points == 1 else 's'}\n(Submitted in <#{proposal.submissionChannel.channelId}>)")
                        e.set_image(url = proposal.url)
                        await msg.edit(embed = e)

                channelSuperFinal = await bot.fetch_channel(SUPERFINAL)

                for i, proposal in enumerate(categ.top3ofCategory()):
                    e = discord.Embed(description = f"**Photo #{i+1} for {categ.name}**\nSubmitted in <#{proposal.submissionChannel.channelId}>")
                    e.set_image(url = proposal.url)
                    await channelSuperFinal.send(embed = e)

                save()

    @bot.command(name = "recap_semis")
    async def recap_semis(ctx = None):
        if ctx is None or ctx.author.id == ADMIN_ID:
            for channelObj in LANGUAGE_CHANNELS.values():
                affi += f"{len(channelObj.proposals)} photos have been submitted in this thread so far. The top 5 will reach the semi-final\n"

                await (ctx.channel if ctx else await bot.fetch_channel(channelObj.channelId)).send(affi)

    @bot.command(name = "start_gf1")
    async def startgf1(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = await bot.fetch_channel(SUPERFINAL)
            msgVote = await channel.send("React with 🧀 to vote for the best photo of food\nReact with 🎨 to vote for the best photo of art-architecture-monuments\nReact with 🍂 to vote for the best photo of nature-landscapes\nReact with 🐈 to vote for the best photo of pets-wildlife")

            for nomCateg, emoji in (("food", "🧀"), ("art", "🎨"), ("nature", "🍂"), ("pets", "🐈")):
                election = Election("RankedPairs")
                election.commence = True
                categ = CATEGORIES[nomCateg]
                categ.election = election

                async for msg in channel.history(limit = None, oldest_first = True):
                    if msg.embeds == []:
                        continue

                    e = msg.embeds[0]
                    if nomCateg in e.description.lower():
                        nomPhoto = e.description.split("\n")[0].replace("*", "")
                        url = e.image.url
                        photo = [x for x in categ.proposals if x.url == url][0]

                        election.candidats.add(photo)
                        election.nom2candidat[nomPhoto] = photo
                        election.candidat2nom[photo] = nomPhoto

                GRAND_FINALS[msgVote.id, emoji] = (election, list(election.nom2candidat.items()))
                await msgVote.add_reaction(emoji)
                save()

    @bot.command(name = "stop_gf1")
    async def stopgf1(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = await bot.fetch_channel(SUPERFINAL)

            for nomCateg in ("food", "art", "nature", "pets"):
                categ = CATEGORIES[nomCateg]
                electionCateg = categ.election 

                electionCateg.calculVote()
                classement = electionCateg.getResultats()
                
                if classement == []: continue #pas de résultats pour la catégorie. ne devrait pas arriver…
                winner = classement[0][0]
                categ.setWinner(winner)

                await channel.send(f"**Results of the vote for {categ.name}:**")
                msgs, details, fichiers = electionCateg.affi()

                trophies = ["🥇", "🥈", "🥉", "", ""]
                for i, msg in reversed(list(enumerate(msgs))):
                    e = discord.Embed(description = f"{trophies[i]} of the category **{categ.name}**" if i != 0 else f"Winner of the category **{categ.name}** {trophies[i]}")
                    e.set_image(url = classement[i][0].url)
                    await channel.send(msg, embed = e)

                affiDetails = [""]
                for classement, votants in details.items():
                    affiCls = " > ".join(classement) + "\n" + " ".join(f'<@{ident}>' for ident in votants) + "\n"
                    if len(affiCls) + len(affiDetails[-1]) < 2000:
                        affiDetails[-1] += affiCls
                    else:
                        affiDetails.append(affiCls)
                for msg in affiDetails:
                    e = discord.Embed(title = "Detailed results of the vote", description = msg)
                    await channel.send(embed = e)

            GRAND_FINALS.clear()
            save()

    @bot.command(name = "update_country_roles")
    async def update_country_roles(ctx):
        if ctx.author.id == ADMIN_ID:
            for human in HUMANS.values():
                old = human.countryRoles
                user = await ctx.guild.fetch_member(human.userId)
                human.countryRoles = countryRolesUser(user)

            save()
            if ctx: await ctx.message.add_reaction("🗳️")

    @bot.command(name = "recount_votes")
    async def recount_votes(ctx, channel: discord.TextChannel):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channelObj = CATEGORIES[channel.id]
            channelObj.votes = {proposal: set() for proposal in channelObj.proposals}

            async for msg in channel.history():
                if msg.id in channelObj.msg2vote:
                    proposal = channelObj.msg2vote[msg.id]
                    channelObj.votes[proposal] = {getHuman(user) for react in msg.reactions async for user in react.users() if react.emoji == "👍" and user.id != bot.user.id}

            save()
            if ctx: await ctx.message.add_reaction("🗳️")

    @bot.command(name = "start_gf2")
    async def startgf2(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = await bot.fetch_channel(SUPERFINAL)
            msgVote = await channel.send("React with 🗳️ to vote for your preferred photo among the winners of the 4 categories")
            await msgVote.add_reaction("🗳️")

            election = Election("RankedPairs")
            election.commence = True
            for i, nomCateg in enumerate({"food", "art", "nature", "pets"}):
                categ = CATEGORIES[nomCateg]
                if categ.winner is None: continue

                election.candidats.add(categ.winner)
                election.nom2candidat[categ.name] = categ.winner
                election.candidat2nom[categ.winner] = categ.name
                categ.election = election

            GRAND_FINALS[msgVote.id, "🗳️"] = (election, list(election.nom2candidat.items()))
            save()

    @bot.command(name = "stop_gf2")
    async def stopgf2(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = await bot.fetch_channel(SUPERFINAL)

            election = CATEGORIES["food"].election
            election.calculVote()
            classement = election.getResultats()
            winner = classement[0][0]

            await channel.send(f"**Results of the Grand Final - Part 2:**")
            msgs, details, fichiers = election.affi()

            trophies = ["🥇", "🥈", "🥉"] + [""]
            for i, msg in reversed(list(enumerate(msgs))):
                e = discord.Embed(description = f"{trophies[i]} for <@{classement[i][0].author.userId}>" if i != 0 else f"The winner of the Photo Contest is <@{classement[i][0].author.userId}> {trophies[i]}!\nCongrats :partying_face: :tada:")
                e.set_image(url = classement[i][0].url)
                await channel.send(msg, embed = e)

            affiDetails = [""]
            for classement, votants in details.items():
                affiCls = " > ".join(classement) + "\n" + " ".join(f'<@{ident}>' for ident in votants) + "\n"
                if len(affiCls) + len(affiDetails[-1]) < 2000:
                    affiDetails[-1] += affiCls
                else:
                    affiDetails.append(affiCls)
            for msg in affiDetails:
                e = discord.Embed(title = "Detailed results of the vote", description = msg)
                await channel.send(embed = e)

            save()

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id == ADMIN_ID:
            pickle.dump(None, open("save_photo_contest.p", "wb"))
            await ctx.message.add_reaction("👍")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

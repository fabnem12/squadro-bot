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

#token = "" #bot token
#prefix = ","
print(prefix)

#BOT FOR VOLT'S PHOTO CONTEST

ADMIN_ID = 619574125622722560

listOfChannels = [877625594324598875, 877626245582573668, 746208469870182490, 746041800804007988, 568852610648375296, 797238878150590474, 890977089631698964]
#listOfChannels = [890977089631698964, 889250102596743198, 891337824387866644]
#listOfChannels = [802946635906547762, 802946670601568276, 803897141453914162]

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
        return (len(set(country for human in self.votes[proposal] for country in human.countryRoles)) + len(self.votes[proposal]), -proposal.submissionTime)
    def top3ofCategory(self):
        return sorted(self.votes.keys(), key=self.nbPoints, reverse = True)[:3]

class LanguageChannel(Category):
    def addProposal(self, proposal, messageId):
        Category.addProposal(self, proposal)
        Category.setMsgProposal(self, proposal, messageId)

    def top3PerCategory(self):
        return {name: sorted(filter(lambda x: x.category is categ, self.votes.keys()), key=lambda x: (len(self.votes[x]), -x.submissionTime), reverse = True)[:3] for name, categ in CATEGORIES.items() if isinstance(name, int)}

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
                msg2submission[messageId] = (date, channelId, submittedBy, url, 2)

                await msgFrom.edit(content = "Which category fits the most this photo?\n🧀 for Food, 🎨 for Art - Architecture - Monuments 🍂 Nature - Landscapes")
                await msgFrom.add_reaction("🧀")
                await msgFrom.add_reaction("🎨")
                await msgFrom.add_reaction("🍂")
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

async def ajoutDuel(votant, opt1, opt2, channel, election): #crée un message permettant de se positionner sur un duel
    msg = await channel.send(f":arrow_left: {election.candidat2nom[opt1]} or {election.candidat2nom[opt2]} :arrow_right:")
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")

    GRAND_FINALS[msg.id] = (votant, (opt1, opt2))

async def majDuel(msg, votant, opt1, opt2, election):
    await msg.edit(content = f":arrow_left: {election.candidat2nom[opt1]} or {election.candidat2nom[opt2]} :arrow_right:")
    GRAND_FINALS[msg.id] = (votant, (opt1, opt2))

async def grand_final_react(messageId, user, guild, emojiHash, channel, remove = False):
    if not remove and (messageId, emojiHash) in GRAND_FINALS:
        election, categ = GRAND_FINALS[messageId, emojiHash]
        channel = await dmChannelUser(user)
        userId = user.id

        if election.fini():
            await channel.send("The vote is already closed…")
            return

        if not election.isVotant(userId):
            votant = election.getVotant(userId, reset = True)
            for nomPhoto, photo in election.nom2candidat.items():
                e = discord.Embed(description = nomPhoto)
                e.set_image(url = photo.url)
                await channel.send(embed = e)

            await channel.send("I'm asking you your preferred photo in 2 or 3 duels to determine your ranking of the photos, please react with ⬅️ and ➡️ accordingly")

            opt1, opt2 = votant.optionAFaire()
            await ajoutDuel(votant, opt1, opt2, channel, election)
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
            await channel.send("**Your vote has been saved.**\nYou can change your vote by reacting again in <#889539190449131551>")
            save()

def main() -> None:
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=prefix, help_command=None, intents = intents)

    @tasks.loop(minutes = 1.0)
    async def autoplanner():
        from arrow import utcnow
        now = utcnow().to("Europe/Brussels")
        if CONTEST_STATE[2] != 0:
            day = (now.date() - CONTEST_STATE[2]).days #number of days since the beginning of the contest
        else:
            day = 0

        if day == 1:
            if CONTEST_STATE[1] and now.hour == 8 and now.minute == 0:
                await startsemis()
        elif day == 2:
            if CONTEST_STATE[1] and now.hour == 23 and now.minute == 59:
                await endsemis()
        elif day == 3:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "food")
            elif now.hour == 20 and now.minute == 0:
                await stopcateg(None, "food")
        elif day == 4:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "art")
            elif now.hour == 20 and now.minute == 0:
                await stopcateg(None, "art")
        elif day == 5:
            if now.hour == 8 and now.minute == 0:
                await startcateg(None, "nature")
            elif now.hour == 20 and now.minute == 0:
                await stopcateg(None, "nature")
        elif day == 6:
            if now.hour == 8 and now.minute == 0:
                await startgf1(None)
            elif now.hour == 20 and now.minute == 0:
                await stopgf1(None)
        elif day == 7:
            if now.hour == 8 and now.minute == 0:
                await startgf2(None)
            elif now.hour == 20 and now.minute == 0:
                await stopgf2(None)

    @bot.event
    async def on_ready():
        autoplanner.start()

    async def traitementRawReact(payload):
        if payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
            messageId = payload.message_id
            guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
            user = (await guild.fetch_member(payload.user_id)) if guild else (await bot.fetch_user(payload.user_id))
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

    @bot.command(name = "save")
    async def sauvegarde(ctx):
        if ctx.author.id == ADMIN_ID:
            save()

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

                    msgConfirm = await ctx.send("Are you sure that:\n- you took this photo yourself?\n- that it is somewhat related with this channel?\nIf yes, you can confirm the submission with <:eurolike:759798224764141628>", reference = ref)
                    try:
                        msg2submission[msgConfirm.id] = (ctx.message.created_at, ctx.channel.id, ctx.author.id, await resendFile(url), 1)
                    except Exception as e:
                        await msgConfirm.edit(content = "I'm sorry, it seems that this file is too big, I can't handle it :sweat_smile:")
                        await (await dmChannelUser(bog.get_member(ADMIN_ID))).send(str(e))
                    else:
                        await msgConfirm.add_reaction("eurolike:759798224764141628")
                        save()
                else:
                    await ctx.send("You have to post a photo to make a submission. You can check <#889538982931755088> to see how to do it")
            else:
                await ctx.send("Sorry, the submission period hasn't started or is over…")
        else:
            await ctx.send("Submissions for the photo contest aren't allowed in this channel…")

    @bot.command(name = "start_contest")
    async def startcontest(ctx):
        from arrow import utcnow, get

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
                channel = bot.get_channel(channelId)
                await channel.send(f"**Hey! The photo contest is starting now!**\n\nPlease read the submission rules in <#889538982931755088>.\nYou can upvote **as many proposals as you want**, the 3 photos with most upvotes from each category will reach the finals.\nThe 3 categories are: **food**, **art - architecture - monuments** and **nature - landscapes**.")

            CONTEST_STATE[0] = True
            save()

    @bot.command(name = "end_semis")
    async def endsemis(ctx = None):
        if ctx is None or ctx.author.id == ADMIN_ID:
            for key, channel in LANGUAGE_CHANNELS.items():
                channelObj = bot.get_channel(channel.channelId)

                for categname, proposals in channel.top3PerCategory().items():
                    for proposal in proposals:
                        CATEGORIES[categname].addProposal(proposal)

                        nbVotes = len(channel.votes[proposal])
                        e = discord.Embed(description = f"Congrats <@{proposal.author.userId}>, your photo has been selected for the semi-finals!\nIt got {nbVotes} upvote{'' if nbVotes == 1 else 's'}")
                        e.set_image(url = proposal.url)
                        await channelObj.send(embed = e)

            CONTEST_STATE[0] = False
            save()
            if ctx: await ctx.message.add_reaction("👍")

    @bot.command(name = "start_categ")
    async def startcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == ADMIN_ID:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = bot.get_channel(categ.channelId)

                await channel.send("**You can upvote as many photos as you want**\n||Upvotes will be converted into points (number of upvotes + number of country roles of the voters)||\n\n**The top 3 photos will reach the <#889539190449131551>**")

                for proposal in categ.proposals:
                    e = discord.Embed(description = f"React with 👍 to upvote this photo.\nSubmitted in <#{proposal.submissionChannel.channelId}> by <@{proposal.author.userId}>")
                    e.set_image(url = proposal.url)
                    msgVote = await channel.send(embed = e)
                    await msgVote.add_reaction("👍")

                    categ.setMsgProposal(proposal, msgVote.id)
                    save()

    @bot.command(name = "stop_categ")
    async def stopcateg(ctx, categname: str):
        if ctx is None or ctx.author.id == ADMIN_ID:
            if categname in CATEGORIES:
                categ = CATEGORIES[categname]
                channel = bot.get_channel(categ.channelId)

                async for msg in channel.history(limit = None):
                    if msg.id in categ.msg2vote:
                        proposal = categ.msg2vote[msg.id]
                        points, tiebreaker = categ.nbPoints(proposal)
                        e = discord.Embed(description = f"This photo got {points} point{'' if points == 1 else 's'}\n(submitted by <@{proposal.author.userId}> in <#{proposal.submissionChannel.channelId}>)")
                        e.set_image(url = proposal.url)
                        await msg.edit(embed = e)

                channelSuperFinal = bot.get_channel(SUPERFINAL)

                for i, proposal in enumerate(categ.top3ofCategory()):
                    e = discord.Embed(description = f"**Photo #{i+1} for {categ.name}**\nSubmitted in <#{proposal.submissionChannel.channelId}> by <@{proposal.author.userId}>")
                    e.set_image(url = proposal.url)
                    await channelSuperFinal.send(embed = e)

                save()

    @bot.command(name = "start_gf1")
    async def startgf1(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = bot.get_channel(SUPERFINAL)
            msgVote = await channel.send("React with 🧀 to vote for the best photo of food\nReact with 🎨 to vote for the best photo of art-architecture-monuments\nReact with 🍂 to vote for the best photo of nature-landscapes")

            for nomCateg, emoji in (("food", "🧀"), ("art", "🎨"), ("nature", "🍂")):
                election = Election("RankedPairs")
                election.commence = True
                categ = CATEGORIES[nomCateg]

                for i, photo in enumerate(categ.top3ofCategory()):
                    election.candidats.add(photo)
                    election.nom2candidat[f"Photo {i+1} ({categ.name})"] = photo
                    election.candidat2nom[photo] = f"Photo {i+1} ({categ.name})"

                GRAND_FINALS[msgVote.id, emoji] = (election, CATEGORIES[nomCateg])
                await msgVote.add_reaction(emoji)
                save()

    @bot.command(name = "stop_gf1")
    async def stopgf1(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = bot.get_channel(SUPERFINAL)

            for electionCateg, categ in (x for index, x in GRAND_FINALS.items() if isinstance(index, tuple)):
                electionCateg.calculVote()
                classement = electionCateg.getResultats()
                winner = classement[0][0]
                categ.setWinner(winner)

                await channel.send(f"**Results of the vote for {categ.name}:**")
                msgs, fichiers = electionCateg.affi()

                trophies = ["🥇", "🥈", "🥉"] + [""] * (3-len(classement))
                for i, msg in reversed(list(enumerate(msgs))):
                    e = discord.Embed(description = f"{trophies[i]} of the category **{categ.name}**" if i != 0 else f"Winner of the category **{categ.name}** {trophies[i]}")
                    e.set_image(url = classement[i][0].url)
                    await channel.send(msg, embed = e)

                if fichiers:
                    for fichier in fichiers:
                        await ctx.send(file = discord.File(fichier))

            GRAND_FINALS.clear()
            save()

    @bot.command(name = "start_gf2")
    async def startgf2(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = bot.get_channel(SUPERFINAL)
            msgVote = await channel.send("React with 🗳️ to vote for your preferred photo among the winners of the 3 categories")
            await msgVote.add_reaction("🗳️")

            election = Election("RankedPairs")
            election.commence = True
            for i, nomCateg in enumerate({"food", "art", "nature"}):
                categ = CATEGORIES[nomCateg]
                election.candidats.add(categ.winner)
                election.nom2candidat[f"Photo {i+1} {categ.name}"] = categ.winner
                election.candidat2nom[categ.winner] = f"Photo {i+1} {categ.name}"

            GRAND_FINALS[msgVote.id, "🗳️"] = (election, categ)
            save()

    @bot.command(name = "stop_gf2")
    async def stopgf2(ctx):
        if ctx is None or ctx.author.id == ADMIN_ID:
            channel = bot.get_channel(SUPERFINAL)

            for election, _ in (x for index, x in GRAND_FINALS.items() if isinstance(index, tuple)): #seulement un tour de boucle…
                election.calculVote()
                classement = election.getResultats()
                winner = classement[0][0]

                await channel.send(f"**Results of the final vote:**")
                msgs, fichiers = election.affi()

                trophies = ["🥇", "🥈", "🥉"] + [""] * (3-len(classement))
                for i, msg in reversed(list(enumerate(msgs))):
                    e = discord.Embed(description = trophies[i] if i != 0 else f"The winner of the Photo Contest is <@{classement[i][0].author.userId}> {trophies[i]}!\nCongrats :partying_face: :tada:")
                    e.set_image(url = classement[i][0].url)
                    await channel.send(msg, embed = e)

                if fichiers:
                    for fichier in fichiers:
                        await ctx.send(file = discord.File(fichier))

            save()

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id == ADMIN_ID:
            pickle.dump(None, open("save_photo_contest.p", "wb"))
            await ctx.message.add_reaction("👍")

    @bot.command(name = "ayo")
    async def ayo(ctx):
        await ctx.send("ayo")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

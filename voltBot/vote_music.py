import asyncio
import nextcord as discord
import pickle, os
from nextcord.ext import commands
nextcord = discord

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import tokenFVB as token, prefixVolt as prefix, redFlags
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

try:
    if "vote_music.p" in os.listdir():
        JURY, infoVote, votes, authors, songs = pickle.load(open("vote_music.p", "rb"))
    else:
        raise Exception
except:
    JURY = {180333726306140160, 619574125622722560, 745394320739401840, 380720384594411521, 962031267434610759}
    #JURY = {619574125622722560}
    infoVote = {k: [] for k in JURY}
    votes = []
    authors = [619574125622722560, 180333726306140160, 619574125622722560, 962031267434610759, 745394320739401840, 380720384594411521, 745394320739401840, 180333726306140160, 619574125622722560, 962031267434610759, 745394320739401840, 180333726306140160, 619574125622722560, 962031267434610759, 745394320739401840, 380720384594411521, 380720384594411521]
    songs = ["Passacaglia", "Moonlight Sonata", "Prelude", "Ode to Joy", "Four Seasons", "The Final Countdown", "Back in the USSR", "Amsterdam", "Vesoul", "La valse à mille temps", "Padam Padam", "L'hymne à l'amour", "Takogo kak Putin", "Dragostea din tei", "Shum", "Dancing Lasha Tumbai", "Stefania"]

reactionsVote = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
"🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺"]
msgVote = [0]

numberVotesJury = 6
numberMaxVotesPublic = 5
numberMinVotesPublic = 3

#FUNCTIONS #####################################################################
async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm()
    return user.dm_channel

def save():
    pickle.dump((JURY, infoVote, votes, authors, songs), open("vote_music.p", "wb"))

def countVotes():
    jury = dict()
    tele = {e: 0 for e in songs}
    teleDetails = dict()

    pointsJury = lambda top: tuple((e, 12 if i == 0 else (10 if i == 1 else 10-i)) for i, e in enumerate(top))
    pointsTele = lambda rang: 3-rang

    for (username, isJury, top) in votes:
        if isJury:
            jury[username] = pointsJury(top)
        else:
            teleDetails[username] = tuple(top)
            for i, e in enumerate(top):
                tele[e] += pointsTele(i)

    nbPointsJury = 58 * len(jury)

    #tele
    def hare(votes, nbPoints):
        totalVotes = sum(votes.values())
        points = {k: ((nbPoints * p) // totalVotes) if totalVotes > 0 else 0 for k, p in votes.items()}

        if totalVotes > 0:
            for k in sorted(votes, key=lambda x: (nbPoints * votes[x]) % totalVotes, reverse=True)[:nbPoints-sum(points.values())]:
                points[k] += 1

        return points

    idSong = lambda x: songs.index(x) + 1

    #register votes
    with open("data_contest/votes_new.csv", "w") as f:
        printF = lambda *args: f.write(" ".join(str(x) for x in args) + "\n")

        printF("Id;Username;Points")

        #jury
        for juror, recap in jury.items():
            for (song, points) in recap:
                printF(f"{idSong(song)};{juror};{points}")

        #tele
        for (song, points) in hare(tele, nbPointsJury).items():
            printF(f"{idSong(song)};public;{points}")

class ButtonConfirm(nextcord.ui.View):
    def __init__(self, song, remaining, selectPrec):
        super().__init__(timeout = 3600)
        self.value = None
        self.song = song
        self.remaining = remaining
        self.selectPrec = selectPrec

    @nextcord.ui.button(label = "Confirm", style = nextcord.ButtonStyle.blurple)
    async def test(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        top = infoVote[interaction.user.id]
        top.append(self.song)

        self.selectPrec.stop()
        self.stop()

        if self.remaining > 0:
            await interaction.channel.send(f"Select the #{len(top)+1} song you prefer", view=ViewSelect([x for x in songs if x not in top], self.remaining))
            save()
        else:
            await interaction.channel.send(f"**Thanks!**\n\n**Your vote:**\n" + "\n".join(f"**#{i+1}** __{e}__" for i, e in enumerate(top)))
            votes.append((interaction.user.name, interaction.user.id in JURY, tuple(top)))

            infoVote[interaction.user.id] = []
            save()

class ViewSelect(nextcord.ui.View):
    def __init__(self, listSongs, remaining):
        super().__init__(timeout = 3600)
        self.value = None
        self.select = Select(listSongs, remaining, self)
        self.remaining = remaining

        self.add_item(self.select)

class Select(nextcord.ui.Select):
    def __init__(self, listSongs, remaining, view):
        options = [discord.SelectOption(label=e, emoji=r) for r, e in zip(reactionsVote, songs) if e in listSongs]
        super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options)
        self.remaining = remaining
        self.parentView = view

    async def callback(self, interaction: nextcord.Interaction):
        num = len(infoVote[interaction.user.id]) + 1

        async for msg in interaction.channel.history(limit = None):
            if "Confirm" in msg.content: #there is one such message
                await msg.delete()
                break

        await interaction.response.send_message(content=f"Confirm {self.values[0]} as #{num}" + "(you can still select another song thanks to the previous message)", view=ButtonConfirm(self.values[0], self.remaining-1, self.parentView))

async def vote(user, jury: bool):
    channel = await dmChannelUser(user)

    infoVote[user.id] = []
    await channel.send("__**List of songs**__\n\n" + "\n".join(f"- {r} **{e}**" for r, e in zip(reactionsVote, songs)))
    commandMessage = await channel.send("Select the #1 song you prefer", view=ViewSelect(songs, 10 if jury else 3))

async def react_vote(messageId, user, guild, emojiHash, channel):
    if user.bot: return

    if emojiHash == "🗳️" and messageId == msgVote[0] and infoVote[user.id] == []:
        await vote(user, jury=user.id in JURY)

#MAIN ##########################################################################
def main():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="T.", help_command=None, intents = intents)

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

            await react_vote(messageId, user, guild, emojiHash, channel)

    @bot.command(name = "vote")
    async def voteCommand(ctx):
        if ctx.author.id == 619574125622722560:
            for i in range(len(songs) // 10 + 1):
                await ctx.send(f"__**Set #{i+1} of submissions**__", files=[discord.File(f"data_contest/{e}_recap.mp3") for e in songs[10*i:10*i+10]])

            msg = await ctx.send("React with 🗳️ to vote")
            await msg.add_reaction("🗳️")

            msgVote[0] = msg.id

    @bot.command(name = "count")
    async def countCommand(ctx):
        if ctx.author.id == 619574125622722560:
            countVotes()
            await ctx.message.add_reaction("🗳️")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

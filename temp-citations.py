import asyncio
import nextcord as discord
import pickle, os
import time
from nextcord.ext import commands
nextcord = discord

import sys
from constantes import TOKEN as token, prefixVolt as prefix, redFlags
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

try:
    if "vote_citations.p" in os.listdir():
        JURY, infoVote, votes, songs = pickle.load(open("vote_citations.p", "rb"))
    else:
        raise Exception
except:
    JURY = set()
    infoVote = {k: [] for k in JURY}
    votes = []
    songs = ["> Tout baigne !\n- <:Victor_Exposito:777887281574707240>", "> Les gens qui ont codé depuis des années en C++ ou Python, ces gens-là quand ils comptent leurs doigts ils trouvent 9\n- <:Laurent_Rosaz:760831874658074656>", "> La théorie, c'est quand ça marche pas, et on sait pourquoi.\n> La pratique, c'est quand ça marche, et on sait pas pourquoi.\n> La différence entre la pratique et la théorie, c'est qu'en théorie il n'y en a pas et en pratique il y en a\n- <:Laurent_Rosaz:760831874658074656>", "> Prof : Est-ce qu'il y en a qui ont des idées ?\n> Anatole : Oui\n> Prof : Ok ben Anatole garde ton idée\n- Élodie Maignant", "> Le travail d'un chercheur en maths c'est de remplir des feuilles, les jeter à la fin de la journée, et de rentrer chez soi et pleurer\n- <:THIERRY:692791492820992020>", '> <:THIERRY:692791492820992020> _écrit au tableau_ "Ainsi g est-elle dérivable"\n> tout le monde: 😳 \n> <:THIERRY:692791492820992020> : ah oui, "est-elle", mais c\'est du français ça. Bon, je peux retirer le "elle" si ça vous perturbe moins.\nMais madame Ramond est professeure de français, si elle entre dans la salle, elle me trucide', "> Élève : un vecteur qui va dans toutes les directions\n> <:THIERRY:692791492820992020> : Ouuhhhhh sans stupéfiants, je ne sais pas le faire", "> Même ma petite sœur sait calculer des dérivées partielles !\n> _je n'ai pas de petite sœur_\n> Mais même mon grand frère sait les calculer, et j'ai un grand frère !\n> mais enfin\n- <:THIERRY:692791492820992020>", "> Dans mon groupe de TD il y a une sorte de fétichisme pour les coordonnées polaires, je ne sais pas pourquoi vous les aimez tant\n- <:THIERRY:692791492820992020>", "> P(X-X=0) = 1 parce que X-X = 0 c'est quand même assez souvent vrai\n- Alexandre Boyer", "> On va prouver ce théorème, c'est assez long, j'espère que vous avez pris des gâteaux et de quoi boire, et je vous rappelle qu'il est interdit de manger et boire dans cet amphi\n- <:THIERRY:692791492820992020>", "> _on parle des équations de la chaleur_\n> Il me reste 12 minutes pour le montrer, ça risque d'être chaud\n- Dominique Hulin", "> Là vous êtes sur Windows, donc vous jetez la machine à la poubelle\n- Benjamin Graille", "> Heureux qui comme le fleuve peut suivre son cours dans son lit\n- Ouriel Grynszpan", "> Je suis Dieu. et en tant que Dieu, je vous donne un cadeau\n- <:Laurent_Rosaz:760831874658074656>", "> Je suis Dieu et je suis modeste\n- <:Laurent_Rosaz:760831874658074656>", "> Le premier truc qui est sympa avec Alzheimer c'est que tous les jours vous vous levez et rencontrez des gens nouveaux et sympathiques\n> Le deuxième truc qui est sympa avec Alzheimer c'est qu'à Pâques vous pouvez cacher les œufs en chocolat pour vous-mêmes\n> Le troisième truc qui est sympa avec Alzheimer c'est que tous les jours vous vous levez et rencontrez des gens nouveaux et sympathiques\n- <:Laurent_Rosaz:760831874658074656>", "> _il y a 2 profs de stats pour distribuer et 1 seul a corrigé les copies_\n> Le 2e prof en regardant la première copie : c'est sur 10 ou sur 20 ?\n- les 2 profs sont <:Marieanne:931199159237746758> et Alexandre Boyer", "> J'espère que vous allez réussir, parce que je vous aime bien, mais j'en doute.\n- ?"]

print(votes)
timeClickVote = dict()

reactionsVote = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
"🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]
#reactionsVote = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
msgVote = [0]

numberVotesJury = 5
numberMaxVotesPublic = 5
numberMinVotesPublic = 5

#FUNCTIONS #####################################################################
async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm()
    return user.dm_channel

def save():
    pickle.dump((JURY, infoVote, votes, songs), open("vote_citations.p", "wb"))

def countVotes():
    jury = dict()
    tele = {e: 0 for e in songs}
    teleDetails = dict()

    pointsJury = lambda top: tuple((e, 5 - i) for i, e in enumerate(top))

    votesLoc = {i: x for i, x in enumerate(votes)}

    #let's keep only the last 3 votes of non-contestants
    nbVotesNonContestant = dict()

    for (username, isJury, top) in votesLoc.values():
        jury[username] = pointsJury(top)

    idSong = lambda x: reactionsVote.index(x) + 1

    #register votes
    with open("points_citations.csv", "w") as f:
        printF = lambda *args: f.write(" ".join(str(x) for x in args) + "\n")

        printF("Id;Username;Points")

        #jury
        for juror, recap in jury.items():
            for (song, points) in recap:
                printF(f"{idSong(song)};{juror};{points}")

class ButtonConfirm(nextcord.ui.View):
    def __init__(self, song, remaining, selectPrec, listSongs):
        super().__init__(timeout = 3600)
        self.value = None
        self.song = song
        self.remaining = remaining
        self.selectPrec = selectPrec
        self.listSongs = listSongs

    @nextcord.ui.button(label = "Confirmer", style = nextcord.ButtonStyle.blurple)
    async def test(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        top = infoVote[interaction.user.id]
        top[-1] = self.song

        self.selectPrec.stop()
        self.stop()

        button.disabled=True
        await interaction.response.edit_message(view=self)

        if self.remaining > 0:
            await interaction.channel.send(f"Choisis la {len(top)+1}e citation que tu aimes le plus", view=ViewSelect([(r, e) for r, e in self.listSongs if r not in top], self.remaining, self.selectPrec.userId))
            save()
        else:
            await interaction.channel.send(f"**Merci !**\n\n**Ton vote:**\n" + "\n".join(f"**#{i+1}** {e}" for i, e in enumerate(top)))
            votes.append((interaction.user.name, interaction.user.id in JURY, tuple(top)))

            infoVote[interaction.user.id] = []
            save()

class ViewSelect(nextcord.ui.View):
    def __init__(self, listSongs, remaining, userId):
        super().__init__(timeout = 3600)
        self.value = None
        self.select = Select(listSongs, remaining, self)
        self.remaining = remaining
        self.userId = userId

        self.add_item(self.select)

class Select(nextcord.ui.Select):
    def __init__(self, listSongs, remaining, view):
        options = [discord.SelectOption(label=r) for r, e in listSongs]
        super().__init__(placeholder="Selectionner une citation", max_values=1, min_values=1, options=options)
        self.remaining = remaining
        self.parentView = view
        self.listSongs = listSongs

    async def callback(self, interaction: nextcord.Interaction):
        infoUser = infoVote[self.parentView.userId]
        if infoUser != [] and infoUser[-1] is None:
            del infoUser[-1]
        num = len(infoUser) + 1

        async for msg in interaction.channel.history(limit = None):
            if "Confirmer" in msg.content and msg.author.bot: #there is one such message
                await msg.delete()

            break

        if infoUser == [] or infoUser[-1] is not None:
            infoUser.append(None)
            await interaction.response.send_message(content=f"Confirmer {self.values[0]} comme {num}{'e' if num != 1 else 'er'}" + (" (tu peux encore changer avec le message précédent)" if num == 1 else ""), view=ButtonConfirm(self.values[0], self.remaining-1, self.parentView, self.listSongs))

async def vote(user, jury: bool):
    channel = await dmChannelUser(user)

    infoVote[user.id] = []
    songsLoc = [(r, x) for r, (i, x) in zip(reactionsVote, enumerate(songs))]
    await channel.send("__**Liste des citations**__\n\n")
    liste = [f"- {r}\n{e}" for r, e in songsLoc]
    await channel.send("\n\n".join(liste[:10]))
    await channel.send("\n\n".join(liste[10:]))
    commandMessage = await channel.send("Selectionne ta citation préférée", view=ViewSelect(songsLoc, 5 if jury else 5, user.id))

async def react_vote(messageId, user, guild, emojiHash, channel):
    if user.bot: return

    if (user.id in timeClickVote and time.time() - timeClickVote[user.id] > 300) or user.id not in timeClickVote:
        infoVote[user.id] = []

    if emojiHash == "🗳️" and messageId == msgVote[0] and infoVote[user.id] == []:
        JURY.add(user.id)
        await vote(user, jury=True)
        timeClickVote[user.id]= time.time()

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
            msg = await ctx.send("Réagis avec 🗳️ pour voter")
            await msg.add_reaction("🗳️")

            msgVote[0] = msg.id

    @bot.command(name = "count")
    async def countCommand(ctx):
        if ctx.author.id in (619574125622722560, 180333726306140160):
            countVotes()
            await ctx.message.add_reaction("🗳️")

            if ctx.author.id == 180333726306140160:
                msgVote[0] = None
                await get_votes(ctx)

    @bot.command(name = "find_jurors")
    async def find_jurors(ctx):
        guild = bot.get_guild(567021913210355745)
        channel = await guild.fetch_channel(973607562710769674)
        msg = await channel.fetch_message(974728503973007420)
        users = []
        for reac in msg.reactions:
            users += [x.id for x in await reac.users().flatten()]

        save()

    @bot.command(name = "get_votes")
    async def get_votes(ctx):
        if ctx.author.id not in (619574125622722560, 180333726306140160):
            return

        await ctx.send(file=discord.File("points_citations.csv", filename="votes.csv"))

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

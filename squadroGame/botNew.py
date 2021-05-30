import asyncio
import discord
import os
import pickle
import sys
from discord.ext import commands
from random import randint
from time import sleep
from typing import Optional, Union, Dict, Set, Tuple, Union
from partieBot import PartieBot
from tournoi import Tournoi, Elo

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID, cheminOutputs

stockePID()

cheminPickle = os.path.join(cheminOutputs, "squadro.p")
try:
    INFOS = dict() if not os.path.exists(cheminPickle) else pickle.load(open(cheminPickle, "rb"))
except:
    INFOS = dict()

JoueurId = int
MessageId = int

EmojiSquadro = 831932136730787880
EmojiSquadroStr = "squadro:831932136730787880"
REFRESH_CHANNEL = 847488864713048144

if "PARTIES" not in INFOS: INFOS["PARTIES"]: Dict[Union[JoueurId, MessageId], PartieBot] = dict()
PARTIES = INFOS["PARTIES"]

if "TOURNOIS" not in INFOS: INFOS["TOURNOIS"]: Dict[Union[int, MessageId], Tournoi] = dict()
TOURNOIS = INFOS["TOURNOIS"]

if "ELO" not in INFOS: INFOS["ELO"]: Elo = Elo()
ELO = INFOS["ELO"]

def save(): pickle.dump(INFOS, open(cheminPickle, "wb"))
def estAdmin(usrId): return usrId in ADMINS

async def dmChannelUser(user: Union[discord.Member, discord.User]) -> 'discord.Channel':
    if user.dm_channel is None:
        await user.create_dm() #crée le dm channel, et après user.dm_channel est remplacé par l'objet représentant le dm channel
    return user.dm_channel
################################################################################
#UTILE POUR JOUER ##############################################################
async def traitementRawReact(payload, bot) -> dict:
    if payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
        messageId = payload.message_id
        if payload.guild_id:
            guild = bot.get_guild(payload.guild_id)
            user = await guild.fetch_member(payload.user_id)
        else:
            guild = None
            user = await bot.fetch_user(payload.user_id)
        channel = await bot.fetch_channel(payload.channel_id)

        partEmoji = payload.emoji
        emojiHash = partEmoji.id if partEmoji.is_custom_emoji() else partEmoji.name

        return locals()
    else:
        return None

async def react_start(bot, messageId, user, channel, emojiHash) -> None:
    ref = discord.MessageReference(message_id = messageId, channel_id = channel.id)

    if messageId in PARTIES and emojiHash == EmojiSquadro:
        partie = PARTIES[messageId]
        await channel.send(f"<@{user.id}> a rejoint la partie !", reference = ref)

        partieOk = partie.addJoueur(user.id)
        PARTIES[user.id] = partie
        if partieOk:
            await debutPartie(bot, partie)

async def debutPartie(bot, partie) -> None:
    async def miseEnPlace(channelId: Optional['ChannelId'] = None, channel: Optional['discord.Channel'] = None):
        if channel:
            salon = channel
        else:
            salon = await bot.fetch_channel(channelId)

        msgPlateau = await salon.send("Mise en place de la partie...")
        for k in range(1, 5+1):
            await msgPlateau.add_reaction(chr(48+k)+chr(65039)+chr(8419))

        PARTIES[msgPlateau.id] = partie

        msgInfo = await salon.send("Quasiment finie !")
        partie.addRefresh(salon.id, msgPlateau.id, msgInfo.id)

    if partie.salon:
        await miseEnPlace(channelId = partie.salon)
    else:
        for joueurId in partie.joueursHumains():
            dmChannel = await dmChannelUser(await bot.fetch_user(joueurId))
            await miseEnPlace(channel = dmChannel)

    await affichePlateau(bot, partie)

async def react_jeu(bot, messageId, user, channel, emojiHash) -> None:
    reac2coup = {chr(48+k)+chr(65039)+chr(8419): k for k in range(1, 5+1)}

    if messageId in PARTIES and emojiHash in reac2coup:
        partie = PARTIES[messageId]
        coup = reac2coup[emojiHash]

        if partie.finie():
            await channel.send("La partie est déjà finie :tada:")
        else:
            if partie.aQuiLeTour() == user.id:
                if partie.coupValide(coup): #on joue le coup
                    async with channel.typing():
                        partie.faitCoup(coup)
                        await affichePlateau(bot, partie)
                else:
                    await channel.send(f"Coup invalide : {coup}. Les seuls coups valides sont : {', '.join(str(x) for x in range(1, 5+1) if partie.coupValide(x))}")
            else:
                await channel.send("Hé, c'est pas à toi de jouer :angry:")

async def tourIA(bot, partie: PartieBot) -> None:
    coup = partie.coupIA()
    partie.faitCoup(coup)

    if partie.salon:
        channel = await bot.fetch_channel(partie.salon)

    await affichePlateau(bot, partie)

def finPartie(partie: PartieBot) -> None:
    toDelete = [trucId for trucId, part in PARTIES.items() if part is partie]
    for trucId in toDelete:
        del PARTIES[trucId]

    partieGagnee, gagnant = partie.gagnant()
    if partieGagnee:
        ELO.addPartie(*partie.joueursHumains(), gagnant)

    save()

async def affichePlateau(bot, partie: PartieBot) -> None:
    if partie.salon:
        channel = await bot.fetch_channel(partie.salon)

    async def update(urlImg: str, channel) -> None:
        msgPlateau, msgInfo = partie.msgRefresh[channel.id]
        msgPlateauObj = await channel.fetch_message(msgPlateau)
        msgInfoObj = await channel.fetch_message(msgInfo)

        await msgPlateauObj.edit(content = urlImg)
        await msgInfoObj.edit(content = partie.info())

    img = partie.affi()
    if img:
        if partie.refresh:
            channelRefresh = await bot.fetch_channel(REFRESH_CHANNEL)
            msgTmp = await channelRefresh.send(file = discord.File(img))
            urlImg = msgTmp.attachments[0].url
            await msgTmp.delete()

            if partie.salon:
                await update(urlImg, await bot.fetch_channel(partie.salon))
            else:
                for joueurId in partie.joueursHumains():
                    channel = await dmChannelUser(await bot.fetch_user(joueurId))
                    await update(urlImg, channel)
        else:
            if partie.salon:
                await channel.send(file = discord.File(img))
                await channel.send(partie.info())
            else:
                for joueurId in partie.joueursHumains():
                    channel = await dmChannelUser(await bot.fetch_user(joueurId))
                    await channel.send(file = discord.File(img))
                    await channel.send(partie.info())

        if partie.aQuiLeTour() is None and not partie.finie(): #c'est à l'IA de jouer
            if partie.salon:
                async with channel.typing():
                    await tourIA(bot, partie)
            else:
                await tourIA(bot, partie)

        if partie.finie():
            finPartie(partie)
    else:
        await channel.send("Euh il y a un problème d'affichage, là :sweat_smile:")

################################################################################
#UTILE POUR TOURNOI ############################################################
async def demandePlanning(bot, tournoi: Tournoi) -> None:
    txt = "Vous êtes dispos à quelles heures demain ?\n" + " ".join(f"<@{jId}>" for jId in tournoi.participants) + "\n\n" + "\n".join(f":regional_indicator_{chr(97+i)}: {creneau}h" for i, creneau in enumerate(tournoi.creneauxPossibles))
    channel = await bot.fetch_channel(tournoi.salon)

    msgPlanning = await channel.send(txt)

    tournoi.addMsgPlanning(msgPlanning.id)
    TOURNOIS[msgPlanning.id] = tournoi

    for i in range(len(tournoi.creneauxPossibles)):
        await msgPlanning.add_reaction(chr(127462+i))


async def react_planning(bot, messageId, user, channel, emojiHash) -> None:
    if messageId in TOURNOIS:
        tournoi = TOURNOIS[messageId]
        reac2creneau = {chr(127462+i): creneau for i, creneau in enumerate(tournoi.creneauxPossibles)}

        if user.id in tournoi.participants and emojiHash in reac2creneau:
            tournoi.addDispo(user.id, reac2creneau[emojiHash])
################################################################################
#MAIN ##########################################################################
def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None, intents = discord.Intents.all())

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_raw_reaction_add(payload):
        traitement = await traitementRawReact(payload, bot)
        if traitement:
            messageId = traitement["messageId"]
            user = traitement["user"]
            guild = traitement["guild"]
            emojiHash = traitement["emojiHash"]
            channel = traitement["channel"]

            await react_start(bot, messageId, user, channel, emojiHash)
            await react_jeu(bot, messageId, user, channel, emojiHash)
            await react_planning(bot, messageId, user, channel, emojiHash)

    @bot.event
    async def on_raw_reaction_remove(payload):
        await on_raw_reaction_add(payload)

    @bot.command(name = "start_here") #par défaut : dans le salon courant, avec refresh et sans ia
    async def start(ctx, affiMoutons: Optional[str]):
        ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)

        if ctx.author.id in PARTIES:
            await ctx.send("Vous êtes déjà dans une partie...", reference = ref)
        else:
            #on crée une nouvelle partie
            partie = PartieBot(refresh = True, salon = ctx.channel.id, moutons = (True if affiMoutons else False))
            joueursFinis = partie.addJoueur(ctx.author.id)

            msgDebut = await ctx.send(f"Ok {ctx.author.mention}, tu seras joueur 1 !\nPour rejoindra la partie en tant que joueur 2, quelqu'un doit réagir avec <:{EmojiSquadroStr}>.")
            await msgDebut.add_reaction(EmojiSquadroStr)

            #on l'enregistre pour l'utiliser plus tard
            PARTIES[ctx.author.id] = partie
            PARTIES[msgDebut.id] = partie

    @bot.command(name = "sheep_here")
    async def sheep(ctx):
        await start(ctx, "sheep")

    @bot.command(name = "start_ia")
    async def startIA(ctx, idIa: int):
        ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)

        if ctx.author.id in PARTIES:
            await ctx.send("Vous êtes déjà dans une partie...", reference = ref)
        elif idIa not in (1, 2):
            await ctx.send("L'IA est forcément joueur 1 ou joueur 2...", reference = ref)
        else:
            #on crée une nouvelle partie
            partie = PartieBot(ia = idIa-1, refresh = True, salon = None, moutons = False)
            partie.addJoueur(ctx.author.id)

            #on va envoyer la réponse en dm à la personne qui joue contre elle-même
            dmChannel = await dmChannelUser(ctx.author)

            msgDebut = await dmChannel.send(f"Ok {ctx.author.mention}, tu seras joueur {3-idIa} et l'IA sera joueur {idIa}")
            await debutPartie(bot, partie)

            PARTIES[ctx.author.id] = partie
            PARTIES[msgDebut.id] = partie

    @bot.command(name = "forfait")
    async def forfait(ctx):
        partie = PARTIES[ctx.author.id]
        if partie.salon:
            channel = await bot.fetch_channel(partie.salon)
            await channel.send(f"<@{ctx.author.id}> a déclaré forfait !")
        else:
            for joueurId in partie.joueursHumains():
                channel = await dmChannelUser(await bot.fetch_user(joueurId))
                await channel.send(f"<@{ctx.author.id}> a déclaré forfait !")

        finPartie(partie)

    @bot.command(name = "start_tournoi")
    async def startTournoi(ctx, channel: discord.TextChannel, *participants: discord.Member):
        idTournoi = randint(1000000, 9999999)
        tournoi = Tournoi([x.id for x in participants], channel.id, idTournoi)
        TOURNOIS[idTournoi] = tournoi

        await ctx.send(f"idTournoi : {idTournoi}")
        await demandePlanning(bot, tournoi)
        save()

    @bot.command(name = "elo")
    async def scoreElo(ctx, someone: Optional[Union[discord.User, str]]):
        if isinstance(someone, str):
            someone = None
        elif someone is None:
            someone = ctx.author

        await ctx.send(f"{someone.mention if someone else 'Monte Squadro'} a un score Elo de {ELO.score(someone.id if someone else None)} pour Squadro")

    @bot.command(name = "add_elo")
    async def add_elo(ctx, someone: discord.Member, elo: float):
        if estAdmin(ctx.author.id):
            ELO.setScore(someone.id, elo)

            await ctx.message.add_reaction("👌")
            save()

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

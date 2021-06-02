import asyncio
import discord
import os
import pickle
import sys
from arrow import get as arrowGet, utcnow
from discord.ext import commands, tasks
from random import randint
from time import sleep
from typing import Optional, Union, Dict, Set, Tuple, Union
from partieBot import PartieBot
from tournoi import Tournoi, Elo

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID, cheminOutputs, decoupeMessages

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
                        save()
                        await affichePlateau(bot, partie)
                else:
                    await channel.send(f"Coup invalide : {coup}. Les seuls coups valides sont : {', '.join(str(x) for x in range(1, 5+1) if partie.coupValide(x))}")
            else:
                await channel.send("Hé, c'est pas à toi de jouer :angry:")

async def tourIA(bot, partie: PartieBot) -> None:
    coup = partie.coupIA()
    partie.faitCoup(coup)

    #if partie.salon:
    #    channel = await bot.fetch_channel(partie.salon)

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

            for observateurId in partie.observateurs:
                observateur = await bot.fetch_channel(observateurId)
                await observateur.send(urlImg)
                await observateur.send(partie.info())
        else:
            if partie.salon:
                await channel.send(file = discord.File(img))
                await channel.send(partie.info())
            else:
                for joueurId in partie.joueursHumains():
                    channel = await dmChannelUser(await bot.fetch_user(joueurId))
                    await channel.send(file = discord.File(img))
                    await channel.send(partie.info())

        if partie.aQuiLeTour() is None and not partie.finie(): #c'est à l'IA de jouer.
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
    if tournoi.duelsAFaire == []:
        nouveauxDuels = tournoi.faitTour()

        if nouveauxDuels != []:
            txtDuels = "Voilà les duels pour demain :\n\n"
            txtDuels += "\n".join(f"{f'<@{a}>' if a else 'Monte Squadro'} VS {f'<@{b}>' if b else 'Monte Squadro'}" for a, b in nouveauxDuels)

            txt = "Vous êtes dispos à quelles heures demain ?\n" + " ".join(f"<@{jId}>" for jId in tournoi.participants) + "\n\n" + "\n".join(f":regional_indicator_{chr(97+i)}: {creneau}h" for i, creneau in enumerate(tournoi.creneauxPossibles))
            channel = await bot.fetch_channel(tournoi.salon)

            await channel.send(txtDuels) #on envoie l'annonce des duels
            msgPlanning = await channel.send(txt)

            tournoi.addMsgPlanning(msgPlanning.id)
            TOURNOIS[msgPlanning.id] = tournoi

            for i in range(len(tournoi.creneauxPossibles)):
                await msgPlanning.add_reaction(chr(127462+i))
        else:
            channel = await bot.fetch_channel(tournoi.salon)
            await channel.send("Il n'y a plus de duel à faire selon le bot.")

async def react_planning(bot, messageId, user, channel, emojiHash) -> None:
    if messageId in TOURNOIS:
        tournoi = TOURNOIS[messageId]
        reac2creneau = {chr(127462+i): creneau for i, creneau in enumerate(tournoi.creneauxPossibles)}

        if user.id in tournoi.participants and emojiHash in reac2creneau:
            tournoi.addDispo(user.id, reac2creneau[emojiHash])

async def trucsAFaireTournoi(bot):
    tournois = []
    for tournoi in TOURNOIS.values():
        if tournoi not in tournois: tournois.append(tournoi)

    now = utcnow().to("Europe/Brussels")
    if now.minute != 0:
        return

    #on regarde s'il faut lancer des matchs
    for tournoi in tournois:
        matchsHeure = tournoi.matchsHeure(now.hour)

        if matchsHeure != []:
            for index, (a, b) in enumerate(matchsHeure):
                salonId = tournoi.salon2 if index else tournoi.salon #a priori il n'y a pas plus de deux matchs en même temps…
                salon = await bot.fetch_channel(salonId)

                if a is None:
                    partie = PartieBot(refresh = True, salon = salonId, ia = 0)
                    partie.addJoueur(b)
                    await salon.send(f"<@{b}> c'est l'heure de jouer contre l'IA ! Tu seras joueur 2 (avec les pions rouges)")
                elif b is None:
                    partie = PartieBot(refresh = True, salon = salonId, ia = 1)
                    partie.addJoueur(a)
                    await salon.send(f"<@{a}> c'est l'heure de jouer contre l'IA ! Tu seras joueur 1 (avec les pions jaunes)")
                else:
                    partie = PartieBot(refresh = True, salon = salonId)
                    partie.addJoueur(a)
                    partie.addJoueur(b)
                    await salon.send(f"<@{a}> et <@{b}>, c'est l'heure de votre match !")

                tournoi.addPartie(partie, (a, b))
                partie.addObservateur(tournoi.salonObservateur)

                save()
                await debutPartie(bot, partie)

        #on regarde aussi s'il y a des matchs lancés il y a une heure qui n'ont pas avancé d'un iota
        for partie in tournoi.partiesEnCours:
            duel = tournoi.partiesEnCours[partie]
            heureMatch = tournoi.heureMatch(duel)
            if heureMatch and heureMatch < now.hour:
                #on regarde si le match a avancé ou pas

                #pas -> cas 1 : toujours au joueur 1, une seule situation (celle de départ)
                if partie.partie.idJoueur == 0 and len(partie.situations) == 1:
                    #le joueur 1 est défaillant, on donne la victoire au joueur 2
                    partie.partie.gagnant = 1
                    await affichePlateau(bot, partie)
                elif partie.partie.idJoueur == 1 and len(partie.situations) == 2:
                    #le joueur 2 est défaillant, on donne la victoire au joueur 1
                    partie.partie.gagnant = 0
                    await affichePlateau(bot, partie)
                elif partie.finie():
                    #on enregistre les résultats de la partie dans le tournoi
                    tournoi.enregistreFinPartie(partie)

    #on lance le calcul du planning pour chaque tournoi à 8h
    if now.hour == 8:
        for tournoi in tournois:
            planningOk = tournoi.calculPlanning()
            save()

            salon = await bot.fetch_channel(tournoi.salon)

            if planningOk:
                txtPlanning = "Voilà le planning des matchs de la journée :\n\n"
                txtPlanning += "\n".join(f"{f'<@{a}>' if a else 'Monte Squadro'} VS {f'<@{b}>' if b else 'Monte Squadro'} à {tournoi.heureMatch((a,b))}h" for a, b in tournoi.planning)

                await salon.send(txtPlanning)
            else:
                await salon.send("Je n'ai pas réussi à faire moi-même le planning. Help me <@619574125622722560> :pray:")

################################################################################
#MAIN ##########################################################################
def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None, intents = discord.Intents.all())

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @tasks.loop(minutes = 1.0)
    async def plannifTournoi():
        await trucsAFaireTournoi(bot)

    @bot.event
    async def on_ready():
        try:
            plannifTournoi.start()
        except RuntimeError:
            pass

    @bot.event
    async def on_raw_reaction_add(payload, remove = False):
        traitement = await traitementRawReact(payload, bot)
        if traitement:
            messageId = traitement["messageId"]
            user = traitement["user"]
            guild = traitement["guild"]
            emojiHash = traitement["emojiHash"]
            channel = traitement["channel"]

            if not remove:
                await react_start(bot, messageId, user, channel, emojiHash)

            await react_jeu(bot, messageId, user, channel, emojiHash)
            await react_planning(bot, messageId, user, channel, emojiHash)

    @bot.event
    async def on_raw_reaction_remove(payload):
        await on_raw_reaction_add(payload, remove = True)

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
        if ctx.author.id in PARTIES:
            partie = PARTIES[ctx.author.id]
            if partie.salon:
                channel = await bot.fetch_channel(partie.salon)
                await channel.send(f"<@{ctx.author.id}> a déclaré forfait !")
            else:
                for joueurId in partie.joueursHumains():
                    channel = await dmChannelUser(await bot.fetch_user(joueurId))
                    await channel.send(f"<@{ctx.author.id}> a déclaré forfait !")

            finPartie(partie)
        else:
            await ctx.message.add_reaction("❔")

    @bot.command(name = "start_tournoi")
    async def startTournoi(ctx, channel: discord.TextChannel, channel2: discord.TextChannel, channelObservateur: discord.TextChannel, *participants: discord.Member):
        idTournoi = randint(1000000, 9999999)
        tournoi = Tournoi([x.id for x in participants], channel.id, channel2.id, channelObservateur.id, idTournoi, ELO)
        TOURNOIS[idTournoi] = tournoi

        await ctx.send(f"idTournoi : {idTournoi}")
        await demandePlanning(bot, tournoi)
        save()

    @bot.command(name = "classement_tournoi")
    async def classementTournoi(ctx, ident: Optional[int]):
        if ident is None:
            tournois = list(set(TOURNOIS.values()))
            if len(tournois) == 1:
                ident = tournois[0].id

        if ident in TOURNOIS:
            tournoi = TOURNOIS[ident]

            txtClassement = "Voici le classement actuel du tournoi :\n\n"
            txtClassement += "\n".join(f"**{index+1}** {(await ctx.guild.fetch_member(joueurId)).name}" for index, joueurId in enumerate(sorted(tournoi.participants, key=lambda x: (tournoi.nbVictoires[x], ELO.score(x)), reverse = True)))

    @bot.command(name = "del_tournoi")
    async def delTournoi(ctx, idTournoi: int):
        if estAdmin(ctx.author.id) and idTournoi in TOURNOIS:
            del TOURNOIS[idTournoi]

            await ctx.message.add_reaction("👌")
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

    @bot.command(name = "liste_tournois")
    async def listeTournois(ctx):
        if estAdmin(ctx.author.id):
            await ctx.send(str(TOURNOIS))

    @bot.command(name = "liste_parties")
    async def listeParties(ctx):
        if estAdmin(ctx.author.id):
            await ctx.send(str(PARTIES))

    @bot.command(name = "infos_tournoi")
    async def infosTournoi(ctx, idTournoi: int):
        if estAdmin(ctx.author.id) and idTournoi in TOURNOIS:
            txt = str(TOURNOIS[idTournoi].__dict__)
            msgs = decoupeMessages([txt])

            for msg in msgs:
                await ctx.send(msg)

    @bot.command(name = "infos_partie")
    async def infosTournoi(ctx, idPartie: int):
        if estAdmin(ctx.author.id) and idTournoi in PARTIES:
            txt = str(PARTIES[idTournoi].__dict__)
            msgs = decoupeMessages([txt])

            for msg in msgs:
                await ctx.send(msg)

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

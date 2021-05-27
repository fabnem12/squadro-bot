import asyncio
import discord
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID

stockePID()

def main():
    import time
    from discord.ext import commands
    from random import choice, randint

    from algoTournoi import genereToursPossibles, mariagesStables
    from Partie import Partie

    PHASE_TESTS = False

    #Tuto pour faire un bot discord : https://realpython.com/how-to-make-a-discord-bot-python/

    partieEnCours = None #on va stocker la partie dans une variable globale, comme ça on n'a pas à la relancer à chaque fois
    situationsConnues = dict() #idem pour les situationsConnues, comme ça l'IA apprendra d'une partie sur l'autre
    MINI_DEPART = "10000000000"
    joueurs = dict()
    parties = dict()
    partiesParJoueur = dict()
    minisParPartie = dict()

    partiesTournoi = dict()
    ordreInitTournoi = []

    cacheSBest = dict()

    bot = commands.Bot(command_prefix=prefixeBot, help_command=None)

    @bot.event
    async def on_ready():
        pass#bot.loop.create_task(pixel())

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_raw_reaction_add(payload):#pour l'assignation automatique des rôles
        if payload.channel_id in {756964371498008586, 775399351514038323, 782610674886377534, 690333214535188665}:
            channel = await bot.fetch_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            guild = msg.guild
            user = await guild.fetch_member(payload.user_id)

            role = None
            if payload.channel_id == 756964371498008586: #accueil serveur maths
                emoji = str(payload.emoji)

                if msg.id == 771661485722042399 and emoji == "🧑‍🏫": #on ajoute le rôle Sensibilisation
                    role = guild.get_role(771647658770038824)

            if payload.channel_id == 775399351514038323: #concours L2 info
                if msg.id == 775406166645538817:
                    role = guild.get_role(775399948967084052)

            if payload.channel_id == 782610674886377534: #salon rôles MPI
                if msg.id == 782611725966245949:
                    role = guild.get_role(756864601022267442) #ping-revisions-ldd

            if payload.channel_id == 690333214535188665: #accueil L2 MPI-LDD
                if msg.id == 692062222582546432:
                    role = guild.get_role(772745936291102730) #rôle L2

            if role:
                await user.add_roles(role)
                channelUser = await dmChannelUser(user)
                await channelUser.send("C'est noté {}, tu as bien reçu le rôle \"{}\" !".format(user.mention, role.name))

    @bot.event
    async def on_message(msg):
        if msg.author.id == 689536409060900933: return #le bot ne devrait pas réagir à lui-même

        if "squadro " in msg.content.lower():
            if msg.guild.id == 690209463369859129:
                if msg.channel.id != 712391173980946464:
                    await msg.channel.send("Envie de jouer à Squadro ? Vous pouvez lancer une partie dans le salon <#712391173980946464> avec la commande {pf}start".format(pf = prefixeBot))
                else:
                    await msg.channel.send("Vous pouvez lancer une partie qui se joue en MP avec la commande **{pf}start**. Pour plus voir d'options, lancez la commande **{pf}help**".format(pf = prefixeBot))

        await bot.process_commands(msg)

    async def affichePlateau(ctx, partie):
        if partie is not None:
            async with ctx.typing():
                img = partie.affichePlateau(moutons = parties[partie]["moutons"])
                if img:
                    await ctx.send(file=discord.File(img))

    async def dmChannelUser(user):
        if user.dm_channel is None:
            await user.create_dm()
        return user.dm_channel

    def estAdmin(user):
        return user.id in ADMINS

    def nbPointsTournoi():
        victoires = dict()
        for infosPartie in partiesTournoi.values(): #on regarde les détails des parties pour compter les points
            if type(infosPartie) != dict: continue #il peut aussi y avoir des "Partie" dans les valeurs
            joueurs = infosPartie["joueurs"]

            for joueur in joueurs:
                if joueur not in victoires: victoires[joueur] = []

            if joueurs[0] is infosPartie["gagnant"]: victoires[joueurs[0]].append(joueurs[1])
            elif joueurs[1] is infosPartie["gagnant"]: victoires[joueurs[1]].append(joueurs[0])

        nbPoints = dict()
        for joueur, vaincus in victoires.items(): nbPoints[joueur] = len(vaincus)

        return nbPoints, victoires

    def nouveauTourTournoi():
        candidatsTries = list(sorted())

    async def finPartie(ctx, partie, victoire = True, idForfait = None):
        joueurs = parties[partie]["joueurs"].copy()

        #on prévient l'admin numéro 0 aka moi que la partie est finie
        channelMoi = await dmChannelUser(bot.get_user(ADMINS[0]))
        if len(joueurs) > 1: #tous les joueurs ont été déclarés (sinon on est à un début de partie avorté...)
            await channelMoi.send("La partie {} vs {} est finie".format(joueurs[0].mention, joueurs[1].mention))

        if victoire:
            idGagnant = partie.gagnant
            gagnant = joueurs[idGagnant]
            perdant = joueurs[1-idGagnant]

            if parties[partie]["dansSalon"]:
                await affichePlateau(ctx, partie)

                await ctx.send("{} a cordialement écrasé {} !!!!!!".format(gagnant.mention, perdant.mention))
            else:
                for joueur in (gagnant, perdant):
                    channel = await dmChannelUser(joueur)
                    await affichePlateau(channel, partie)
                    await channel.send("{} a cordialement écrasé {} !!!!!!".format(gagnant.mention, perdant.mention))

        if partie in partiesTournoi: #si c'est une partie de tournoi, on enregistre aussi le gagnant
            idPartie = partiesTournoi[partie]
            del partiesTournoi[partie] #l'enregistrement ici ne servait que de flag pour identifier que c'est une partie de tournoi

            if not victoire and idForfait is not None: #il y a un joueur qui a déclaré forfait pour arrêter la partie, c'est l'autre qui est gagnant
                gagnant = joueurs[1-idForfait]
            #si ce test est faux, c'est que victoire vaut True, donc gagnant est déjà correctement initialisé

            #on enregistre alors le gagnant
            partiesTournoi[idPartie]["gagnant"] = gagnant

        #on supprime les traces de la partie
        for joueur in joueurs:
            if joueur in partiesParJoueur: #dans le cas (dégénéré) où il y a une partie user vs lui-même, il ne faut pas faire le del
                del partiesParJoueur[joueur]
        del parties[partie]

    async def phaseTestsMsg(ctx):
        if PHASE_TESTS and (ctx.guild is not None and "Tests Squadro Discord" not in ctx.guild.name):
            await ctx.send("Le bot est en phase de tests donc temporairement désactivé. Retour prévu dans le courant de l'après-midi")
            return True
        return False

    @bot.command(name="sheep")
    async def sheep(ctx, here = "non"):
        await demarrage(ctx, here, True)

    @bot.command(name='start') #au démarrage d'une nouvelle partie
    async def demarrage(ctx, here = "non", moutons = ""):
        global partieEnCours
        stop = await phaseTestsMsg(ctx)
        if stop: return

        here = str(here).lower()
        moutons = True if moutons else False #True aussi si ce champ est un str non vide
        user = ctx.author

        if here.startswith("-") and estAdmin(ctx.author): #pour lancer une partie de tournoi dont les joueurs sont pré-enregistrés
            idPartieAnticipee = here.replace(" ", "")
            if idPartieAnticipee in partiesTournoi and partiesTournoi[idPartieAnticipee]["gagnant"] is None:
                partie = Partie(situationsConnues, MINI_DEPART, True, False, False, False, True)

                joueurs = partiesTournoi[idPartieAnticipee]["joueurs"]

                #on initialise la partie comme une partie "normale"
                parties[partie] = {"joueurs":joueurs, "dansSalon": ctx.channel, "moutons": moutons}
                partiesParJoueur[joueurs[0]] = partie
                partiesParJoueur[joueurs[1]] = partie

                #on enregistre dans partiesTournoi l'instance de la partie pour identifier que c'est une partie de tournoi
                partiesTournoi[partie] = idPartieAnticipee

                await ctx.send("La partie {} VS {} va commencer !".format(joueurs[0].mention, joueurs[1].mention))
                await affichePlateau(ctx, partie)
                await ctx.send("À votre tour, joueur 1 {}. Vous jouez les pions jaunes/horizontaux".format(joueurs[0].mention))

                minisParPartie[partie] = [MINI_DEPART]

                return
            else:
                return

        if user not in partiesParJoueur: #le joueur lance une nouvelle partie
            await ctx.send("Démarrage d'une nouvelle partie...")

            IA1 = "ia1" in here
            IA2 = not IA1 and "ia2" in here #on empêche les parties IA vs IA

            partieEnCours = Partie(situationsConnues, MINI_DEPART, True, True, IA1, IA2, True)

            if IA1:
                joueurs = [1]
            elif IA2:
                joueurs = [2]
            else:
                joueurs = []

            parties[partieEnCours] = {"joueurs":joueurs, "dansSalon": ctx.channel if "here" in here else False, "moutons": moutons}
            await ctx.send("En attente de joueurs...\nPour se déclarer joueur, il faut écrire **{pf}moi**. Le joueur 1 doit se déclarer en premier, puis le joueur 2.".format(pf = prefixeBot))

        else: #le joueur est déjà dans une partie
            await ctx.send("Vous participez déjà à une partie, vous ne pouvez pas participer à plusieurs parties en même temps.")
            await ctx.send("Vous pouvez déclarer forfait dans votre partie en cours si vous le souhaitez avec la commande {pf}forfait".format(pf = prefixeBot))

        return

    @bot.command(name='moi')
    async def moi(ctx):
        global partieEnCours
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if ctx.author in partiesParJoueur and parties[partiesParJoueur[ctx.author]]["joueurs"] != [ctx.author]: #on ne laisse pas un joueur jouer à 2 parties en même temps
            await ctx.send("Vous êtes déjà dans une partie en cours. Impossible de vous laisser participer à 2 parties en même temps, désolé...")
            return

        if partieEnCours is not None:
            infosPartie = parties[partieEnCours]
            channel = ctx.channel if infosPartie["dansSalon"] else await dmChannelUser(ctx.author)

            if ctx.author not in infosPartie["joueurs"]: #on peut ajouter le joueur sans pb
                if len(parties[partieEnCours]["joueurs"]) == 0 or parties[partieEnCours]["joueurs"][0] == 2:
                    await channel.send("Bienvenue, joueur 1 {}. Vous jouerez les pions jaunes/horizontaux.".format(ctx.author.mention))
                else:
                    await channel.send("Bienvenue, joueur 2 {}. Vous jouerez les pions rouges/verticaux.".format(ctx.author.mention))
            else: #easter egg, on laisse la possibilité de jouer contre soi-même
                await channel.send("Vous êtes schizophrène ? On dirait bien. Je vous laisse jouer entre vous.")

            parties[partieEnCours]["joueurs"].append(ctx.author)
            if parties[partieEnCours]["joueurs"][0] == 2:
                del parties[partieEnCours]["joueurs"][0]
                parties[partieEnCours]["joueurs"].append(2)

            partiesParJoueur[ctx.author] = partieEnCours

            if len(parties[partieEnCours]["joueurs"]) == 2: #la partie compte 2 joueurs, on peut arrêter l'appel à des nouveaux joueurs
                #on envoie un message pour appeler le premier joueur à jouer
                joueurEnCours = parties[partieEnCours]["joueurs"][partieEnCours.idJoueur]

                minisParPartie[partieEnCours] = [MINI_DEPART]

                channelJEnCours = await dmChannelUser(joueurEnCours)
                channel = ctx.channel if infosPartie["dansSalon"] else channelJEnCours

                await channel.send("À votre tour, {}".format(joueurEnCours.mention))
                await affichePlateau(channel, partieEnCours)

                await ctx.send("La partie commence {} !".format("" if parties[partieEnCours]["dansSalon"] else "en MP"))

                if joueurEnCours == 1:
                    partieEnCours.interaction()

                partieEnCours = None
            else: #on a besoin d'un 2e joueur
                await ctx.send("En attente d'un 2e joueur...")
                #ctx et pas channel vu qu'il faut envoyer le message dans le salon, et pas en MP au joueur 1 !

        else: #il n'y a pas de partie lancée
            await ctx.send("Il n'y a pas de partie lancée. Faites {pf}start pour lancer une nouvelle partie".format(pf = prefixeBot))

    @bot.command(name='coup')
    async def coup(ctx, coup, joueur = ""): #pour préciser qu'on veut un coup entier
        stop = await phaseTestsMsg(ctx)
        if stop: return

        user = ctx.author if joueur == "" or not estAdmin(ctx.author) else bot.get_user(int(joueur))

        if user not in partiesParJoueur: #l'utilisateur ne joue pas dans une partie, on le rejette
            await ctx.send("Vous ne pouvez pas jouer sans être dans une partie ! Vous pouvez lancer une partie avec {pf}start".format(pf = prefixeBot))
            return

        partie = partiesParJoueur[user]
        channel = parties[partie]["dansSalon"] if parties[partie]["dansSalon"] else await dmChannelUser(user)

        if parties[partie]["dansSalon"] and ctx.channel != parties[partie]["dansSalon"]:
            await ctx.send("Vous ne pouvez pas jouer ici, il faut jouer dans le salon <#{}> du serveur **{}**".format(channel.id, channel.guild.name))
            return

            if user != parties[partie]["joueurs"][partie.idJoueur]:
                await channel.send("Patience ! Ce n'est pas encore votre tour.")
            else: #c'est le bon joueur
                if "random" in str(coup).lower():
                    coup = randint(1, 5)
                    await ctx.send("Coup au hasard : {}".format(coup))
                    coup = int(coup)

                    coupOk = partie.interaction(coup)

                if coupOk: #le coup est valide, normalement partie a changé son idJoueur, donc on peut trouver l'identifiant du joueur suivant pour l'appeler
                    #on enregistre la nouvelle mini dans minisParPartie
                    minisParPartie[partie].append(partie.mini())

                    if not parties[partie]["dansSalon"]: await affichePlateau(channel, partie)
                    idJoueurSuivant = partie.idJoueur #pour savoir si un joueur est IA, c'est partie.joueurs[idJoueur].estIA

                    if partie.finPartie(): #la partie est finie
                        await finPartie(ctx, partie)
                        return
                    else:
                        #on dit au joueur qui a fini que la balle est dans le camp adverse
                        if not parties[partie]["dansSalon"]: await channel.send("L'autre joueur réfléchit...")

                        #on récupère la channel du joueur adverse
                        joueurSuivant = parties[partie]["joueurs"][idJoueurSuivant]

                        channelUser = await dmChannelUser(joueurSuivant)
                        channel = ctx.channel if parties[partie]["dansSalon"] else channelUser
                        await affichePlateau(channel, partie)

                        await channel.send("À votre tour, joueur {} {}".format(idJoueurSuivant+1, joueurSuivant.mention)) #à n'afficher que si le joueur suivant est humain
                        #On peut faire une commande affichant le pourcentage de chance de gagner x) -> en fait l'affichage se fait tout seul quand on appelle Joueur.IA_coup()
                else:
                    await channel.send("Z'avez pas le droit de jouer ce coup !")


    @bot.command(name="show")
    async def show(ctx):
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if ctx.author in partiesParJoueur:
            partie = partiesParJoueur[ctx.author] #on retrouve la partie du joueur ayant demandé à voir le plateau
            joueurEnCours = parties[partie]["joueurs"][partie.idJoueur]
            await affichePlateau(ctx, partie)
            await ctx.send("C'est au joueur {} {} de jouer".format(partie.idJoueur+1, joueurEnCours.mention))
        elif ctx.author in partiesParJoueur or (estAdmin(ctx.author) and len(parties) == 1):
            partie = partiesParJoueur[ctx.author] if ctx.author in partiesParJoueur else list(parties.keys())[0]
            await affichePlateau(ctx, partie)
            await ctx.send("Le joueur {} ({}) a environ {}% de chances de gagner à ce stade".format(gagnant+1, parties[partie]["joueurs"][gagnant].mention, round(pourcentage, 2)))
        else: #l'utilisateur n'est dans aucune partie
            await ctx.send("Vous ne pouvez pas utiliser cette commande sans être dans une partie.")

    @bot.command(name='debug')
    async def debug(ctx):
        global partieEnCours
        stop = await phaseTestsMsg(ctx)
        if stop: return

        channel = await dmChannelUser(ctx.author)

        if estAdmin(ctx.author):
            await channel.send("admins : {}\n".format(ADMINS))

            affi = "ordreInitTournoi : \n"
            affi += "\n".join(["**{}** {}".format(index+1, x.name) for index, x in enumerate(ordreInitTournoi)])
            await channel.send(affi)

            affi = "partiesTournoi : \n"
            for idPartie, infos in partiesTournoi.items():
                if type(infos) == str: continue
                affi += "idPartie : {}, joueurs : {} VS {} (gagnant : {})\n".format(idPartie, infos["joueurs"][0].name, infos["joueurs"][1].name, infos["gagnant"])
            await channel.send(affi)

            await channel.send("parties en cours : {}\n".format(parties))
            for partie in parties:
                await affichePlateau(channel, partie)
                await channel.send("Mini plateau : {}".format(partie.mini()))
                await channel.send("Partie {} VS {}".format(parties[partie]["joueurs"][0].name, parties[partie]["joueurs"][1].name))

    @bot.command(name="add_partie")
    async def add_partie(ctx, identifiants, idGagnant = ""):
        if estAdmin(ctx.author):
            idGagnant = None if idGagnant == "" else int(idGagnant)
            idJoueur1, idJoueur2 = map(int, identifiants.split("-"))

            if idJoueur1-1 < len(ordreInitTournoi) and idJoueur2-1 < len(ordreInitTournoi):
                joueur1, joueur2 = ordreInitTournoi[idJoueur1-1], ordreInitTournoi[idJoueur2-1]
            else:
                joueur1 = bot.get_user(idJoueur1)
                joueur2 = bot.get_user(idJoueur2)

            if None in (joueur1, joueur2):
                await ctx.send("L'un des joueurs au moins est invalide !")
                return

            lettres = "azertyuiopqsdfghjklmwxcvbn0123456789"
            idPartie = ""
            while idPartie == "" or idPartie in partiesTournoi:
                idPartie = "-"+"".join([choice(lettres) for _ in range(5)])

            #on enregistre la partie
            if idGagnant == "": gagnant = None
            elif (type(idGagnant) == str and idGagnant.isdigit()) or type(idGagnant) == int:
                idGagnant = int(idGagnant)

                if idGagnant-1 < len(ordreInitTournoi):
                    gagnant = ordreInitTournoi[idGagnant-1]
                else:
                    gagnant = bot.get_user(idGagnant)
            else:
                gagnant = None

            partiesTournoi[idPartie] = {"joueurs":[joueur1, joueur2], "gagnant":gagnant}

            channel = await dmChannelUser(ctx.author)
            await channel.send("Partie ok. Id : {}, joueurs : {} vs {}".format(idPartie, joueur1.name, joueur2.name))

    @bot.command(name="delete_partie")
    async def delete_partie(ctx, idPartie):
        if estAdmin(ctx.author):
            idPartie = idPartie.replace(" ", "")

            if idPartie in partiesTournoi:
                del partiesTournoi[idPartie]

                await ctx.send("Partie {} supprimée".format(idPartie))

    @bot.command(name='forfait')
    async def arret(ctx):
        global partieEnCours
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if ctx.author in partiesParJoueur:
            partie = partiesParJoueur[ctx.author]
            infosPartie = parties[partie]

            idJoueurForfait = 0 if infosPartie["joueurs"][0] == ctx.author else 1

            #on déclare le forfait
            if infosPartie["dansSalon"]:
                await ctx.send("Le joueur {} a déclaré forfait !".format(ctx.author.mention))
            elif len(infosPartie["joueurs"]) == 2: #on n'affiche pas ce message si on fait forfait d'une partie avortée où l'on est le seul joueur
                for joueur in infosPartie["joueurs"]:
                    channel = await dmChannelUser(joueur)
                    await channel.send("Le joueur {} a déclaré forfait face à {} !".format(ctx.author.mention, infosPartie["joueurs"][1-idJoueurForfait].mention))
            else:
                await ctx.send("OK")

            #fin de la partie
            await finPartie(ctx, partie, False, idForfait=idJoueurForfait)

            partieEnCours = None
        else:
            await ctx.send("Vous n'avez pas le droit de déclarer forfait sans être joueur.\nVous pouvez cependant lancer une partie si vous le voulez avec {pf}start".format(pf = prefixeBot))



    @bot.command(name="back") #pour revenir à la position précédente
    async def back(ctx):
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if ctx.author not in partiesParJoueur:
            await ctx.send("Vous ne pouvez pas utiliser cette commande sans être dans une partie !")
            return

        partie = partiesParJoueur[ctx.author]
        infosPartie = parties[partie]

        if len(minisParPartie[partie]) < 2:
            await ctx.send("Vous ne pouvez pas utiliser cette commande au début de la partie !")
            return

        miniPrec = minisParPartie[partie][-2] #on récupère la mini de la situation précédente

        #on fait une nouvelle partie qui part de là
        nouvPartie = Partie(situationsConnues, miniPrec, True, False, False, False, True)

        #on met à jour les enregistrements qu'il faut
        for joueur in infosPartie["joueurs"]:
            partiesParJoueur[joueur] = nouvPartie
        joueurEnCours = infosPartie["joueurs"][partie.idJoueur]

        parties[nouvPartie] = infosPartie.copy()
        del parties[partie]

        minisParPartie[nouvPartie] = minisParPartie[partie][:-1]
        del minisParPartie[partie]

        #on demande au joueur en cours de rejouer
        await affichePlateau(ctx, nouvPartie)
        await ctx.send("À votre tour joueur {} {}".format(nouvPartie.idJoueur+1, joueur.mention))

    @bot.command(name="best")
    async def best(ctx, identifiantJoueur = "0"):
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if identifiantJoueur.isdigit():
            identifiantJoueur = int(identifiantJoueur)
            joueur = bot.get_user(identifiantJoueur)
        else:
            joueur = ctx.author

        if ctx.author in partiesParJoueur or len(parties) == 1:
            partie = None

            if ctx.author not in partiesParJoueur and joueur is None and len(parties) != 1:
                return
            elif ctx.author in partiesParJoueur:
                joueur = ctx.author
            elif len(parties) == 1:
                partie = list(parties.keys())[0]
            elif joueur in partiesParJoueur:
                pass
            else:
                return

            listeMembresChannel = [] if "members" not in dir(ctx.channel) else ctx.channel.members
            if partie is None: partie = partiesParJoueur[joueur]
            joueurs = parties[partie]["joueurs"]

            channel = ctx

            if partie in partiesTournoi and ctx.author in joueurs and ctx.author.id == 193233316391026697:
                await ctx.send("Vous n'avez pas le droit d'utiliser cette commande pendant le tournoi")
                return
            elif partie in partiesTournoi and ctx.channel is not None and (joueurs[0] in listeMembresChannel or joueurs[1] in listeMembresChannel):
                channel = await dmChannelUser(ctx.author)

            if partie.mini() in cacheSBest:
                idGagnant, pourcentage = cacheSBest[partie.mini()]
            else:
                idGagnant, pourcentage = partie.mieuxPlace()
                cacheSBest[partie.mini()] = (idGagnant, pourcentage)

            if pourcentage < 50: pourcentage = 100-pourcentage
            await channel.send("Le joueur {} ({}) a environ {}% de chances de gagner à ce stade".format(idGagnant+1, joueurs[idGagnant], round(pourcentage, 2)))
        else:
            channel = await dmChannelUser(ctx.author)
            await channel.send("Vous n'êtes dans aucune partie, je ne peux pas vous répondre sur ça.")


    @bot.command(name='rules') #Pour redemander les règles du jeu
    async def rules(ctx):
        imagesRules = [discord.File(os.path.join(os.path.dirname(__file__), "graphics/rules{}.png").format(x)) for x in range(7)]
        await ctx.send(files=imagesRules)
        await ctx.send("**Précision importante** : quand une pièce est retournée, elle change de vitesse.\nUn pion qui se déplace de 1 case à l'aller se déplace de 3 au retour, et vice-versa.\nLes pions qui se déplacent de 2 cases à l'aller ne changent pas au retour.")

    @bot.command(name='help')
    async def help(ctx, submodule = ""):
        if "python" in submodule: return #c'est l'aide python qui est demandée, gérée par botpython.py

        messageAide = """
        Pour lancer une partie de Squadro qui se jouera en MP, utilisez la commande **{pf}start**.
        **{pf}start here** permet de jouer la partie dans le salon où elle a été lancée.
        Une fois une partie lancée, il faut se déclarer pour pouvoir y jouer. C'est possible
        avec **{pf}moi**. Quand deux joueurs se sont déclarés, la partie commence !
        Si vous avez besoin d'un rappel des règles du jeu, **{pf}rules**.
        Pour déplacer un pion, disons le n°**4**, il faut écrire **{pf}coup 4**.
        Pour redemander à voir le plateau de jeu, c'est **{pf}show**.
        Besoin d'annuler le dernier coup ? **{pf}back**

        Besoin de finir la partie avant la fin ? La commande **{pf}forfait** est faite pour ça.
        Envie de savoir qui a le plus de chances de gagner ? C'est **{pf}best**.

        NOUVEAU : vous pouvez utiliser un plateau vert gazon avec des pions en forme de moutons,
        en utilisant la commande **{pf}sheep** et **{pf}sheep here** au lieu de **{pf}start**.

        Ce bot permet aussi d'exécuter du code Python directement dans discord. Pour plus d'informations, **{pf}help python**
        {msgMaintenance}
        """.format(pf = prefixeBot, msgMaintenance = "\n\n**NOTE : LE BOT EST EN MAINTENANCE ACTUELLEMENT, DONC INACCESSIBLE**" if PHASE_TESTS else "")

        await ctx.send(embed = discord.Embed(description = messageAide, title = "Bot Squadro"))

    @bot.command(name="classementTournoi") #classement des joueurs du tournoi
    async def classementTournoi(ctx):
        stop = await phaseTestsMsg(ctx)
        if stop: return

        if estAdmin(ctx.author) and len(partiesTournoi) >= 1:
            nbPoints, victoires = nbPointsTournoi()
            await ctx.send("Classement du tournoi :")

            for index, (joueur, points) in enumerate(sorted(nbPoints.items(), key=lambda x:(x[1], x[0].id), reverse=True)):
                txtVictoires = "" if points == 0 else "(contre {})".format(", ".join([str(x) for x in victoires[joueur]]))
                await ctx.send("**{}** {} avec {} points {victoires}".format(index+1, joueur.mention, points, victoires=txtVictoires))

    @bot.command(name="gagnant") #pour que je force un gagnant si la partie est gagnée d'avance mais que le bot refuse de l'admettre
    async def gagnantForce(ctx, identifiant:int):
        if not estAdmin(ctx.author): return

        joueur = bot.get_user(identifiant)
        if len(parties) == 1 and joueur is None: joueur = parties[list(parties.keys())[0]]["joueurs"][identifiant-1]

        if joueur in partiesParJoueur:
            partie = partiesParJoueur[joueur]
            partie.gagnant = parties[partie]["joueurs"].index(joueur)

            await finPartie(ctx, partie)

    @bot.command(name="setAdmin") #pour ajouter un admin à partir de son identifiant
    async def setAdmin(ctx, identifiant:int):
        nouvAdmin = bot.get_user(identifiant)
        if estAdmin(ctx.author) and identifiant not in ADMINS:
            ADMINS.append(identifiant)
            await ctx.send("{} a été ajouté comme admin".format(nouvAdmin.mention))

    @bot.command(name="ordreInit")
    async def ordreInit(ctx, infos):
        if not estAdmin(ctx.author): return

        identifiants = [int(x) for x in infos.split("-")]
        ordreInit = [bot.get_user(int(identifiant)) for identifiant in identifiants]

        if None not in ordreInitTournoi:
            for i in range(len(ordreInitTournoi)): del ordreInitTournoi[0]
            ordreInitTournoi.extend(ordreInit)

            #l'ordre init est bon, on annonce les premiers tours du tournoi et on les enregistre
            duels = [(premier, ordreInit[len(ordreInit) // 2 + index]) for index, premier in enumerate(ordreInit[:len(ordreInit) // 2])]
            await ctx.send("Voici les duels du premier tour :")

            for joueur1, joueur2 in duels:
                await add_partie(ctx, "{}-{}".format(joueur1.id, joueur2.id))
                await ctx.send("Joueur 1 : {} VS Joueur 2 : {}".format(joueur1.mention, joueur2.mention))
        else:
            await ctx.send("Pas OK")

    @bot.command(name="tourSuivantTournoi")
    async def tourSuivantTournoi(ctx, non = ""):
        if not estAdmin(ctx.author): return

        rencontres = [tuple(infos["joueurs"]) for infos in partiesTournoi.values() if type(infos) != dict and infos["gagnant"] is not None]
        nbPoints, _ = nbPointsTournoi()

        duelsNouveauTour, penalites = genereToursPossibles(ordreInitTournoi, nbPoints, rencontres)

        if non.lower().replace(" ", "") != "bis":
            duelsNouveauTour, penalites = mariagesStables(ordreInitTournoi, nbPoints, rencontres)

        if duelsNouveauTour is None:
            await ctx.send("Il n'est pas possible de faire un tour supplémentaire (où tout le monde participe). Il est donc temps de faire une finale !")
        else:
            await ctx.send("Voici les duels du tour de demain :")
            print(len(duelsNouveauTour))
            for joueur1, joueur2 in duelsNouveauTour:
                await add_partie(ctx, "{}-{}".format(joueur1.id, joueur2.id))
                await ctx.send("Joueur 1 : {} VS Joueur 2 : {}".format(joueur1.mention, joueur2.mention))

            channelMoi = await dmChannelUser(bot.get_user(ADMINS[0]))
            await channelMoi.send("Nb random : {}".format(str(penalites)[:1000]))

    @bot.command(name="add_joueur_tournoi")
    async def add_joueur_tournoi(ctx, identifiant:int):
        if not estAdmin(ctx.author): return

        joueur = bot.get_user(identifiant)
        if joueur is not None and joueur not in ordreInitTournoi:
            ordreInitTournoi.append(joueur)

            await ctx.send("Ajout de {} ok".format(joueur.mention))

    @bot.command(name="remove_joueur_tournoi")
    async def remove_joueur_tournoi(ctx, identifiant):
        if not estAdmin(ctx.author): return

        for joueur in ordreInitTournoi.copy():
            if joueur.id == int(identifiant):
                ordreInitTournoi.remove(joueur)
                await ctx.send("OK, {} retiré".format(joueur.mention))

    @bot.command(name="stop_en_cours")
    async def stop_en_cours(ctx):
        if not estAdmin(ctx.author): return

        for cle in dict(partiesParJoueur):
            del partiesParJoueur[cle]
        for cle in dict(parties):
            del parties[cle]

    #bot.run(TOKEN)
    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

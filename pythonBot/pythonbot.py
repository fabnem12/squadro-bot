import asyncio
import nextcord as discord
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot, GROUPES_DISCORD
from utils import stockePID, cheminOutputs
from edtImg import genereEDT, nomFichierEDT
from SquadroBot import brainfuckSquadroBot, getPlot

stockePID()

NOTEBOOKS = dict()
RAB_TEMPS = set()

DELAI_RAB = 120 #en secondes, combien de temps faut-il attendre avant d'avoir de nouveau du rab ?
DUREE_EXEC = 5
DUREE_EXEC_ADMIN = 120
DUREE_EXEC_RAB = 60

commandesInterdites = ["input(", "open(", "= open", "=open", "exec(", "eval("]
importsAutorises = {"cmath", "math", "matplotlib", "numpy", "pandas", "random", "SquadroBot", "time", "scipy", "pythonBot", "functools", "timeit"}
substituts = {"%ptrlib": "from SquadroBot import ptrlib\nglobals().update(ptrlib())", "%llistlib": "from SquadroBot import linkedlistlib\nglobals().update(linkedlistlib())", "plt.show()": "getPlot()"}
substituts.update({"%matplotlib inline": ""})

estAdmin = lambda user: user.id in ADMINS

def traitementImageEnvoyeeDiscord():
    pass

def checkSyntax(code):
    import ast

    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, e

class Notebook:
    def __init__(self):
        self.glob = dict()
        self.messages = [""] #stocke les messages de print
        self.fichiers = [] #stocke les noms des fichiers de getFile
        self.print = lambda x: x
        self.getFile = lambda x: x

        #on met quelques constantes de base dans le notebook
        self.setConstantes()

        self.morceauxCodeOrd = ["def getFile(nomFichier):\n  from IPython.display import Image, display\n  display(Image(filename = nomFichier))\n\ndef getPlot():\n  import matplotlib.pyplot as plt\n  plt.show()" + "\nfrom cmath import*; arg = phase\nimport numpy as np\nimport matplotlib.pyplot as plt"] #tous les morceaux de code de l'user
        self.msgIdToMorceauId = dict() #dico qui à un id de msg associe son index dans self.morceauxCodeOrd
        self.reponses = [[None]] * len(self.morceauxCodeOrd) #qui à un id de message associe les msg de réponse
        self.images = []


    def setConstantes(self):
        glob = self.glob

        #on importe les fonctions math complexes
        exec("from cmath import *; arg = phase", glob)
        exec("import SquadroBot", glob) #import automatique du module SquadroBot
        exec("import numpy as np")
        exec("import matplotlib.pyplot as plt")

        #ajout des fonctions Re et Im complexes et de l'unité imaginaire en tant que i
        #+ autres fonctions standard qui sont utiles
        from SquadroBot import i
        def helpSquadro(truc):
            helpString = truc.__doc__ if "__doc__" in dir(truc) else "Aide indisponible..."
            if "__builtins__" in dir(truc) and "__doc__" in truc.__builtins__:
                helpString = helpString or truc.__builtins__["__doc__"]

            return str(helpString)
        helpSquadro.__doc__ = "Fonction pour afficher de l'aide"

        messages = self.messages
        def ajoutMsg(*args, end = "\n"):
            messages[0] += " ".join(str(x) for x in args) + end
        ajoutMsg.__doc__ = print.__doc__
        self.print = ajoutMsg

        fichiers = self.fichiers
        def getFile(*nouvFichiers):
            fichiers.extend(nouvFichiers)
        getFile.__doc__ = "getFile(nomFichier1, nomFichier2, nomFichier3, ...) : télécharger des fichiers depuis l'environnement du bot"
        self.getFile = getFile

        quitEasterEgg = lambda *args: ajoutMsg("Bien essayé, mais vous ne pouvez pas utiliser la fonction quit/exit ici")


        def comp(f, g):
            return lambda z: f(g(z))
        def compMieux(*fonctions): #pour composer n fonctions
            res = lambda z: z
            for fonc in fonctions:
                res = comp(res, fonc)

            return res

        brainfuck = brainfuckSquadroBot(ajoutMsg)

        def getPlotEffectif():
            fichiers.append(getPlot())
        getPlotEffectif.__doc__ = "substitut à plt.show, pour afficher un plot"

        import numpy
        import matplotlib.pyplot

        glob.update({"Re": lambda x: complex(x).real, "Im": lambda x: complex(x).imag, "i": i, "help": helpSquadro, "print": ajoutMsg, "getFile": getFile, "brainfuck": brainfuck, "quit": quitEasterEgg, "getPlot": getPlotEffectif, "comp": compMieux})
        glob.update({"np": numpy, "plt": matplotlib.pyplot})

        #(si on a utilisé i comme variable de parcours de range, on peut récupérer sa bonne valeur avec le SquadroBot)

    def ajoutExex(self, msgPlusId, reponses, images):
        code, idMsg = msgPlusId
        self.morceauxCodeOrd.append(code)
        self.msgIdToMorceauId[idMsg] = len(self.morceauxCodeOrd) - 1

        self.reponses.append([None if x is None else x.embeds[0].description for x in reponses])
        self.images.append([])

    def updateCode(self, newMsgPlusId):
        code, idMsg = newMsgPlusId
        index = self.msgIdToMorceauId[idMsg]
        self.morceauxCodeOrd[index] = code

    def toIPYNB(self, idUser: int) -> str:
        notebookDico = {
            "cells": [],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                        "language-info": {"codemirror_mode": {"name": "ipython", "version": 3},
                                            "file_extension": ".py",
                                            "mimetype": "text/x-python",
                                            "name": "python",
                                            "nbconvert_exporter": "python",
                                            "pygments_lexer": "ipython3",
                                            "version": "3.7.0"}
            },
            "nbformat": 4,
            "nbformat_minor": 1
        }

        #on ajoute les blocs de code dans le dico représentant le notebook
        cellulesNotebook = notebookDico["cells"]

        for index, message in enumerate(self.morceauxCodeOrd):
            lignesMsg = message.split("\n")
            reponses = self.reponses[index]
            if len(reponses) > 0 and reponses[0] is None:
                reponses = []

            msg = {
                "cell_type": "code",
                "execution_count": index + 1,
                "metadata": {},
                "outputs": [{"data": {"text/plain": [x + "\n" for x in rep.split("\n")]}, "execution_count": index + 1, "metadata": {}, "output_type": "execute_result"} for rep in reponses],
                "source": [x + "\n" for x in lignesMsg[:-1]] + [lignesMsg[-1]] #on ne met pas le saut de ligne à la fin du bloc
            }
            cellulesNotebook.append(msg)

        nomFichier = "outputs/{}.ipynb".format(idUser)

        import json
        with open(nomFichier, "w") as f:
            json.dump(notebookDico, f)

        return nomFichier

    def toPY(self, idUser: int) -> str:
        codePython = ""
        for index, codeBloc in enumerate(self.morceauxCodeOrd):
            codePython += codeBloc + "\n\n"

        nomFichier = "outputs/{}.py".format(idUser)
        with open(nomFichier, "w") as f:
            f.write(codePython)

        return nomFichier

async def verifCode(code, channel, message):
    trucInterdit = None
    syntaxeOk, erreurSyntaxe = False, None
    safe = True

    if "```python" in code: retire = "```python"
    elif "```py" in code: retire = "```py"
    elif "```brainfuck" in code:
        code = code.replace("```brainfuck\n", '```py\na = """')
        indexFin = code.rfind("```")
        code = code[:indexFin] + '"""\nbrainfuck(a)\n```'

        retire = "```py"
    elif "```sh" in code and estAdmin(message.author):
        indexDebut = code.find("```sh\n") + 6
        indexFin = code.rfind("```")
        code = code[indexDebut:indexFin].replace('"', '\\"')

        sautLigne = "\n"
        code += f"```py\ncmds = [{', '.join(str(tuple(ligne.replace(sautLigne, '').split(' '))) for ligne in code.split(sautLigne) if len(ligne) > 1)}]\n"
        code += "import subprocess\nfor cmd in cmds:\n  output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]\n  print(output.decode('utf-8'))\n```"

        retire = "```py"
    else:
        retire = None
        safe = False

    if safe:
        code = code[code.index(retire) + len(retire):]
        code = code[code.index("\n") + 1:]

        if "```" in code:
            code = code[:code.index("```")]

            for substitut, remplacement in substituts.items():
                code = code.replace(substitut, remplacement)

            safe = True
            for commande in commandesInterdites: #on regarde s'il y a des commandes interdites dans le code
                if commande in code:
                    safe = False
                    trucInterdit = commande
                    break

            #safe = safe or estAdmin(message.author) #les admins peuvent utiliser python sans filtre

            if safe:
                syntaxeOk, erreurSyntaxe = checkSyntax(code)
                if syntaxeOk:
                    #on vérifie que les imports sont ok
                    #pour cela, on exécute seulement les lignes d'import, on regarde les variables globales de type "module"
                    #et on voit s'il y en a qui ne sont pas autorisés
                    globModules = dict()
                    try:
                        for ligne in (x for x in code.split("\n") if "import" in x and "\"" not in x and "'" not in x):
                            exec(ligne, globModules)
                    except Exception as e: #import invalide, on dit stop
                        await channel.send("Erreur : {}".format(e))
                        safe = False
                else:
                    safe = False

            if safe:
                for _, module in ((nom, val) for nom, val in globModules.items() if type(val) == type(os)): #on ne vérifie que les objets de type module
                    nomModule = module.__name__.split(".")[0]
                    #.split(".")[0] -> isoler le nom principal du module (éliminer les sous-modules, matplotplib.pyplot -> matplotlib)

                    if nomModule not in importsAutorises:
                        safe = False
                        trucInterdit = "L'import du module **" + nomModule + "** est __interdit__"
                        break

            if estAdmin(message.author):
                safe, trucInterdit = True, None

            if not syntaxeOk: safe = False #on ne va pas laisser passer une erreur de syntaxe quand même !

    if estAdmin(message.author): safe = True
    if not safe:
        msgEnvoi = ""
        if retire is None:
            await channel.send("Il manque l'indicateur 'python' (ou 'py', ça marche aussi). Je ne gère pas (encore) d'autre langage.")
        elif trucInterdit:
            if "import" in trucInterdit: #message spécial en cas d'import interdit par moi
                await channel.send(trucInterdit)
                await channel.send("Vous pouvez demander à <@619574125622722560> de rajouter des modules.")
            else: #message général sur pourquoi le code ne peut pas être accepté si ce n'est pas un import interdit
                await channel.send("Vous n'avez pas le droit d'utiliser ce morceau de code : ```python\n{}```\nToute réclamation doit être faite à <@619574125622722560>".format(trucInterdit))
        elif not syntaxeOk:
            await channel.send("Erreur de syntaxe quelque part... Vérifiez votre code\nDétail de l'erreur de syntaxe : {}".format(erreurSyntaxe))
        else:
            await channel.send("Le code n'est pas valide (il doit être dans un bloc : \n\`\`\`python\nCODE\n\`\`\`)")

    while code[-1] == "\n": code = code[:-1]

    #on identifie la dernière ligne de code pour l'isoler
    indexLastRow = code.rfind("\n")
    code, fin = code[:indexLastRow+1], code[indexLastRow+1:]
    if fin[0] in (" ", "\t"): #la ligne de fin (exécutée à part) ne peut pas être indentée (donc dans un bloc)
        code += fin
        fin = ""

    return (code, fin), safe

def main(idsTraites = set(range(10))):
    from arrow import get as arrowGet, utcnow
    from nextcord.ext import commands, tasks
    from func_timeout import func_timeout, FunctionTimedOut
    import time
    import traceback

    nonConcerne = lambda user: user.id % 10 not in idsTraites

    bot = commands.Bot(command_prefix=prefixeBot, help_command=None, intents = discord.Intents.all())
    LE_BOT = lambda: bot.user

    ################################################################################
    #GESTION DE L'INTERACTION ######################################################
    ################################################################################
    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante
    async def on_command_error(ctx, error):
        if nonConcerne(ctx.author): return

        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    async def envoiMessages(channel, notebook = None):
        messages = notebook.messages[0].replace("*", "\*").replace("_", "\_")
        if messages == "": return [None]#aucun message à envoyer, on ne fait rien

        #on découpe en morceaux de 2000 caractères si besoin
        messagesNew = []
        if len(messages) <= 2000 and messages != "":
            messagesNew = [messages]
        else:
            messagesNew = [""]
            for ligne in messages.split("\n"):
                ligne += "\n" #le split retire le \n, il faut le remettre

                while len(ligne) > 2000:
                    ligneTronque, ligne = ligne[:2000], ligne[2000:]
                    messagesNew.append(ligneTronque)

                if len(messagesNew[-1] + ligne) > 2000:
                    messagesNew.append("")

                messagesNew[-1] += ligne

        messages = messagesNew

        #on envoie
        msgEnvoyes = []
        for msg in messages:
            if msg == "": continue

            msgEnvoye = await channel.send(embed = discord.Embed(description = "\u200B" + msg))
            await msgEnvoye.add_reaction("🗑️")
            msgEnvoyes.append(msgEnvoye)

            time.sleep(0.4) #astuce pour que tous les messages partent (sinon le bot "renonce" à envoyer les messages après le 5e)

        notebook.messages[0] = ""

        return msgEnvoyes

    async def envoiFichiers(channel, nomsFichiers):
        msgEnvoyes = []
        liensImages = []

        for obj in nomsFichiers:
            if isinstance(obj, tuple):
                nom = obj[0]
            else: #on suppose maintenant que obj est un str
                nom = obj

            try:
                msgEnvoye = await channel.send(file = discord.File(nom))
            except Exception as e:
                msgEnvoye = await channel.send("Fichier indisponible (probablement trop gros) : {}\nDétail de l'erreur : {}".format(nom, e))

            await msgEnvoye.add_reaction("🗑️")
            msgEnvoyes.append(msgEnvoye)

            time.sleep(0.4)

        nomsFichiers.clear()
        return msgEnvoyes, liensImages

    @bot.event
    async def on_reaction_add(reaction, user):
        if nonConcerne(user): return
        leBot = LE_BOT()
        msg = reaction.message
        emoji = str(reaction.emoji)

        if user == leBot or msg.author not in (user, leBot): return
        #if not reaction.message.content.startswith(bot.command_prefix): return #ça concerne le bot de jeu squadro -> euh on dirait que c'est inutile

        if emoji == "🔂" and msg.content.startswith(prefixeBot): #relancer le morceau de code
            await evalue(msg, "")
            #pas de rab autorisé quand on relance le bout de code
        if emoji == "🗑️" and (msg.guild is None or user.guild_permissions.manage_messages or user.guild_permissions.administrator or estAdmin(user)):
            await msg.delete()

    @bot.event
    async def on_reaction_remove(reaction, user): await on_reaction_add(reaction, user)

    @bot.event
    async def on_message(msg):
        if msg.author.id != bot.user.id:
            if "patrick" in msg.content.lower():
                await msg.channel.send("MASSOT ! <:PATRICK:692677586291261480>")
            elif "cochon" in msg.content.lower():
                await msg.channel.send("cochon :pig:")

        await bot.process_commands(msg)

    @bot.event
    async def on_message_delete(message):
        if nonConcerne(message.author): return

        #on efface les sorties correspondant au message
        #TODO
        return

    @bot.event
    async def on_ready():
        await bot.change_presence(activity=discord.Game(name="S.help python"))

    @bot.command(name="help")
    async def helpPython(ctx, python = ""):
        if nonConcerne(ctx.author): return
        if "python" not in python.lower(): return #ce n'est pas l'aide python qui est demandée

        messageAide = """
        Le bot Squadro sait aussi **exécuter du code Python** !

        Pour **exécuter un morceau de code**, vous pouvez utiliser la commande **S.nb**, suivie d'un bloc Python.
        Par exemple :
        S.nb \`\`\`py
        print(42)
        \`\`\`
        (il faut faire "alt gr" + 7 pour écrire les signes avant "python") (il faut appuyer deux fois sur la touche £ sur Mac)

        Ça fonctionne sur le modèle du _notebook_.
        Vous pouvez **enchaîner les blocs de code**, les variables locales sont conservées d'un bloc à l'autre. **C'est comme Jupyter**, qu'on a utilisé en Info111.
        Pour _réinitialiser un notebook_, il faut utiliser la commande **S.new_nb**.

        Chaque bloc de code doit pouvoir être **exécuté en moins de 5 secondes**. Au-delà, le **bot arrête l'exécution** de lui-même.
        Vous pouvez _demander_ un **rab de temps d'exécution**, ce qui permet de faire tourner un code plus long.
        La commande **S.rab** permet de le faire.

        Sur tous les blocs de code, **le bot poste plusieurs réactions** dont celle-ci : 🔂.
        En cliquant dessus, vous pouvez **relancer le bloc de code** _(vous pouvez aussi modifier le code et alors c'est le nouveau code qui est lancé)_

        Enfin, en plus de quelques modules Python courants pour **faire des maths**, le bot a aussi **un module appelé SquadroBot**, que <@619574125622722560> va agrémenter cette année.
        Il contient déjà une fonction qui permet de **représenter des fonctions complexes**. Plus d'infos en exécutant le code `help(SquadroBot)`

        **Have fun!**
        """

        await ctx.send(embed = discord.Embed(description = messageAide, title = "Bot Python by Squadro"))

    ################################################################################
    #MIGRATION AUTOMATIQUE DE RÔLE #################################################
    ################################################################################
    @bot.command(name = "migrate")
    async def migrate(ctx, guildInit: int, roleInit: int, roleTarget: int, guildTarget = None):
        if guildTarget is None: guildTarget = ctx.guild.id
        guildTarget = int(guildTarget)
        guildTarget = bot.get_guild(guildTarget)

        userTarget = await guildTarget.fetch_member(ctx.author.id)
        botTarget = await guildTarget.fetch_member(bot.user.id)

        if userTarget is None or not any(role.permissions.administrator for role in userTarget.roles):
            await ctx.send("Désolé vous devez être admin du serveur cible pour lancer cette commande")
            return

        if botTarget is None or not any(role.permissions.manage_roles or role.permissions.administrator for role in botTarget.roles):
            await ctx.send("Le bot n'est pas dans le serveur cible !")
            return

        guildInit = bot.get_guild(guildInit)
        membres = await guildInit.fetch_members(limit = None).flatten()

        roleInit = guildInit.get_role(roleInit)
        membresRoleInit = {membre.id for membre in membres if roleInit in membre.roles}
        roleTarget = guildTarget.get_role(roleTarget)

        await ctx.send("Migration du rôle '{}' vers '{}'".format(roleInit, roleTarget))

        compte = 0
        try:
            async for membre in guildTarget.fetch_members(limit = None):
                if membre.id in membresRoleInit and roleTarget not in membre.roles:
                    await membre.add_roles(roleTarget)
                    compte += 1
        except Exception as e:
            await ctx.send("Erreur : {}".format(e))
            return
        else:
            await ctx.send("{} personnes du rôle '{}' ont reçu automatiquement le rôle '{}'".format(compte, roleInit, roleTarget))

    ################################################################################
    #GESTION DU RAB DE TEMPS #######################################################
    ################################################################################
    def calIdRab(userId: int) -> str:
        from random import randint, seed

        timeComponent = round(time.time()) // DELAI_RAB
        userComponent = int(str(userId)[:4])

        seed((timeComponent + userComponent) ** userComponent)

        idRab = hex(randint(1e6, 1e7-1))[2:]
        return idRab

    def rabIsOk(user, idRab: str): #on vérifie que l'id de rab est le bon
        return (idRab not in RAB_TEMPS and idRab == calIdRab(user.id)) or (estAdmin(user) and idRab == "illimité")

    def heureDebutCreneau():
        timestamp = (round(time.time()) // DELAI_RAB) * DELAI_RAB
        return arrowGet(timestamp).to("Europe/Brussels")

    @bot.command(name="rab") #pour demander du rab de temps (et l'obtenir le cas échéant)
    async def rab(ctx):
        if nonConcerne(ctx.author): return

        idRab = calIdRab(ctx.author.id)
        heureDebut = heureDebutCreneau()
        heureFin = heureDebut.shift(seconds = DELAI_RAB - 1)

        heureDebutStr = "{}h{}".format(*list(map(lambda x: str(x).zfill(2), (heureDebut.hour, heureDebut.minute))))
        heureFinStr = "{}h{}".format(*list(map(lambda x: str(x).zfill(2), (heureFin.hour, heureFin.minute))))

        if idRab in RAB_TEMPS: #l'user a déjà utilisé son rab de temps
            await ctx.send("Je ne peux pas encore vous donner du rab de temps…\nVous avez droit à un toutes les {} minutes.".format(DELAI_RAB / 60))
        else: #on peut lui donner
            await ctx.send(f"Voici l'id d'autorisation de rab de temps : {idRab}\nPour l'utiliser, il faut l'écrire entre la commande d'appel de la fonction et le code :\n{prefixeBot}.nb ID_AUTORISATION \`\`\`python…\nIl est valide de {heureDebutStr} à {heureFinStr} inclus")

    async def infoRab(rabId: str, ctx, user):
        if rabId.startswith("``"): return False

        rabId = rabId[min(len(rabId) if x not in rabId else rabId.index(str(x)) for x in "abcdef0123456789"):]
        rab = rabIsOk(user, rabId) #on voit si le rab de temps est valide ou pas #[1:] car le premier caractère est faux
        if rab:
            RAB_TEMPS.add(rabId) #on enregistre que le rab a été utilisé
            await ctx.send("⚠️ Votre rab a bien été activé pour ce morceau de code.")

            return True
        elif rabId != "":
            await ctx.send("⚠️ L'id d'autorisation de rab fourni n'est pas/plus valide… Je ne laisse que 5 secondes d'exécution pour ce bloc")
            await ctx.send("Il y en a un nouveau toutes les {} minutes".format(DELAI_RAB // 60))

        return False

    ############################################################################
    #TÂCHES PROGRAMMÉES ########################################################
    ############################################################################

    ################################################################################
    #EASTER-EGGS ###################################################################
    ################################################################################
    @bot.command(name = "joke")
    async def joke(ctx):
        from random import choice

        guild = ctx.guild
        matiere = None

        if guild.id == 762734296414683136: #L2 info
            matiere = "computer science"
        elif guild.id == 756418771664633917: #L2 maths
            matiere = "math"
        elif guild.id == 753312911274934345: #L2 physique
            matiere = "physics"
        elif guild.id == 603692346273693697: #math-info
            matiere = choice(["computer science", "math"])
        elif guild.id == 690209463369859129: #MPI
            matiere = choice(["computer science", "computer science", "math", "math", "math", "physics"])
        else: return

        if matiere:
            await ctx.send("=wolf tell a {} joke".format(matiere))


    @bot.command(name="fibotibo")
    async def fibotibo(ctx):
        if ctx.guild.id == 603692346273693697:
            from time import sleep
            a = 1
            b = 1
            for _ in range(10):
                await ctx.send("<:tibovener:684027734103818253>" * a)
                b += a
                a = b - a

                time.sleep(0.4)
        else:
            await ctx.send("Non x) <:tibovener:684027734103818253>")
    ################################################################################
    #RÉCUPÉRATION DU NOTEBOOK SOUS FORME D'UN FICHIER ##############################
    ################################################################################
    @bot.command(name = "save")
    async def save(ctx):
        if nonConcerne(ctx.author): return

        user = ctx.author.id
        if user not in NOTEBOOKS: return
        notebook = NOTEBOOKS[user]

        lienNotebook = notebook.toIPYNB(user)
        lienPy       = notebook.toPY(user)
        await ctx.send("Fichier jupyter :", file = discord.File(lienNotebook))
        #await ctx.send("Fichier python :", file = discord.File(lienPy))

        await ctx.send("Si vous avez utilisé le module SquadroBot, il faut mettre son code dans le même dossier que le notebook **__en gardant le même nom de fichier__**",
                       file = discord.File("SquadroBot.py"))

    ################################################################################
    #FONCTIONS DE TRAITEMENT DU CODE ###############################################
    ################################################################################
    @bot.command(name="new_nb")
    async def newNb(ctx, dummy = "hello"):
        if nonConcerne(ctx.author): return

        NOTEBOOKS[ctx.author.id] = Notebook()
        if dummy:
            await ctx.send("Votre notebook est prêt. Vous pouvez empiler les blocs de code avec la commande **S.nb**")

    @bot.command(name="nb")
    async def nb(ctx, rab = ""):
        if nonConcerne(ctx.author): return

        if ctx.author.id not in NOTEBOOKS:
            await newNb(ctx, False) #False pour ne pas afficher le message d'ouverture du notebook

        await evalue(ctx, rab)

    @bot.command(name="snb")
    async def snb(ctx):
        if nonConcerne(ctx.author): return

        if 0 not in NOTEBOOKS: NOTEBOOKS[0] = Notebook()
        await evalue(ctx, "", NOTEBOOKS[0])

    @bot.command(name="txt")
    async def txt(ctx):
        channel = ctx.channel

        txt = ""
        async for msg in channel.history(limit = None):
            if msg.startswith("T.txt"): continue

            auteur = msg.author.nick if "nick" in dir(msg.author) else msg.author.name
            txt += "{datetime} {auteur}: {message}\n".format(auteur = auteur, message = msg.content, datetime = msg.created_at.strftime("%d/%m/%Y-%H:%M"))

        nomFichier = "sauvegarde-{}.txt".format(channel.name)
        with open(nomFichier, "w") as f:
            f.write(txt)

        await channel.send(file = discord.File(nomFichier))
        import os

        os.remove(nomFichier)

    async def evalue(ctx, rabId = "", notebook = None):
        if nonConcerne(ctx.author): return

        message = ctx if isinstance(ctx, discord.Message) else ctx.message

        for reaction in message.reactions: #on retire les réactions du bot pour ne garder que les plus récentes...
            await reaction.remove(LE_BOT())

        #on vérifie que le code est acceptable
        code = message.content
        channel = message.channel
        user = message.author
        safe = False
        notebook = notebook or NOTEBOOKS[user.id] #le notebook existe forcément, vu qu'il est créé si besoin lors de l'appel à S.nb

        if user.id != 619574125622722560:
            channelSend = await bot.fetch_channel(776403293429563394)
            await channelSend.send("Par {}".format(user.mention))
            await channelSend.send(code)

        #on vérifie que le code est valide avant de le lancer (imports autorisés, pas de commande interdite...)
        (code, fin), safe = await verifCode(code, channel, message)
        #on vérifie l'id de rab, rab contient le booléen "le rab est-il valide pour l'exécution de ce bloc ?"
        rab = await infoRab(rabId, ctx, user)
        #on sépare le code et la ligne de fin

        #le code est accepté pour être exécuté

        #on exécute le code (ou du moins on essaie)
        #-on définit une fonction print qui en fait stocke les affichages dans une liste, et on les envoie à la fin de l'exécution
        #-puis getFile pour récupérer les fichiers et les envoyer
        fichiers = notebook.fichiers

        #-on récupère (ou pas !) le "notebook" de l'utilisateur (cf fonction notebook)
        #-la magie de python fait qu'il est "automatiquement mis à jour" dans le dico pendant l'exécution du code
        glob = notebook.glob
        glob.update({"user": user})
        ajoutMsg = notebook.print

        #exécution du code à proprement parler
        fail = not safe
        if safe: #on n'exécute pas le code s'il n'est pas safe !
            def eval2(code, receptacle, globals = dict(), locals = dict()):
                receptacle[0] = eval(code, globals, locals)

            async with channel.typing():
                try:
                    timeout = DUREE_EXEC if not estAdmin(user) else DUREE_EXEC_ADMIN
                    if rab: timeout = DUREE_EXEC_RAB #on donne 60 secondes si le rab est activé
                    if rab and rabId == "illimité":
                        exec(code, glob)
                        print("hoe")
                    else:
                        debut = time.time()
                        func_timeout(timeout, exec, args=(code, glob))
                        dureeExec = time.time() - debut

                    #on exécute la dernière ligne comme dans la console python
                    #on affiche la valeur de l'expression sur la dernière ligne, quand c'est possible
                    #receptacle pour la valeur de la dernière ligne - la valeur est enregistrée à l'index 0
                    def runLastRow(methode = eval2):
                        valLigneFin = [None]
                        func_timeout(timeout - dureeExec, methode, args=(fin, valLigneFin, glob))
                        valLigneFin = valLigneFin[0]

                        testType = valLigneFin if type(valLigneFin) != list or len(valLigneFin) < 1 else valLigneFin[0]

                        if "__module__" in dir(type(testType)) and "matplotlib" in type(testType).__module__: #pour détecter qu'on veut afficher le plot de matplotlib
                            exec("getPlot()", glob)
                        elif valLigneFin is not None:
                            ajoutMsg(valLigneFin)

                    try: #on essaie de lancer la dernière ligne et de récupérer la valeur si possible
                        runLastRow()
                    except Exception as e: #ça peut planter si la dernière ligne n'est pas une expression
                        if isinstance(e, SyntaxError): #la dernière ligne n'est pas une expression
                            #erreur de syntaxe, peut-être parce que ce n'est pas une expression eval
                            func_timeout(timeout, exec, args=(fin, glob))
                        else: #ça a planté alors que c'est une expression, on envoie le traceback
                            raise e

                except FunctionTimedOut:
                    ajoutMsg("⚠️ Le temps d'exécution dépasse {} secondes, j'arrête automatiquement…".format(timeout))
                    ajoutMsg("Essayez de séparer le code en morceaux plus courts à exécuter.\nVous pouvez aussi demander un rab de temps d'exécution (1 minute) avec la commande **S.rab**")

                    fail = True
                except: #en cas d'erreur, on envoie le traceback à l'utilisateur
                    tb = traceback.format_exc()

                    for ligne in tb.split("\n"):
                        ajoutMsg(ligne)

                    fail = True

        #le code est fini, on l'affiche fièrement
        for reaction in message.reactions: #on retire les réactions précédentes du bot (par ex l'emoji ratage)
            await reaction.remove(LE_BOT())

        await message.add_reaction("🔂") #voulez-vous relancer le code ?
        await message.add_reaction("✅" if not fail else "❌") #le code a été exécuté

        #on envoie les prints à la fin (pour le moment !)
        msgEnvoyes = await envoiMessages(channel, notebook)
        fichierEnvoyes, imagesEnvoyees = await envoiFichiers(channel, fichiers)

        if notebook:
            msgPlusId = (code + fin, message.id)
            notebookUser = NOTEBOOKS[user.id]
            notebookUser.glob = glob
            notebookUser.ajoutExex(msgPlusId, msgEnvoyes, imagesEnvoyees)

    compteurTB = [0]
    @bot.command(name="tb")
    async def tb(ctx, moins = "add"):
        compteurTB[0] += 1 if moins != "sub" else -1
        await ctx.send("On en est à {} 'tout :bath:' <:VictorExposito_thuglife:777883106630828032>".format(compteurTB[0]))

    compteurIsa = [0]
    @bot.command(name="isa")
    async def isa(ctx, moins = "add"):
        compteurIsa[0] += 1 if moins != "sub" else -1
        await ctx.send("On en est à {} références à Isabelle Adjani <:nicole_bidoit:809431037993680966>".format(compteurIsa[0]))

    compteurEnfait = [0]
    @bot.command(name="enFait")
    async def enFait(ctx, moins = "add"):
        compteurEnfait[0] += 1 if moins != "sub" else -1
        await ctx.send("On en est à {} 'en fait'".format(compteurEnfait[0]))


    @bot.command(name = "màj")
    async def maj(ctx):
        if estAdmin(ctx.author):
            from subprocess import Popen, DEVNULL

            await ctx.message.add_reaction("👌")
            await bot.change_presence(activity=discord.Game(name="en redémarrage"))
            Popen(["python3", "maj.py"], stdout = DEVNULL)

    @bot.command(name = "up_img")
    async def up_img(ctx, name: str):
        if ctx.author.id not in NOTEBOOKS:
            await newNb(ctx, False)

        from matplotlib import image
        import requests

        def downloadFile(url, nomFichier):
            cheminSave = os.path.join(cheminOutputs, nomFichier)
            r = requests.get(url)
            with open(cheminSave, "wb") as f:
                f.write(r.content)
            return image.imread(cheminSave)

        notebook = NOTEBOOKS[ctx.author.id]
        imgs = [downloadFile(x.url, x.filename) for x in ctx.message.attachments if ".png" in x.filename or ".jpg" in x.filename]
        if len(imgs) == 1:
            notebook.glob[name] = imgs[0]

            await ctx.message.add_reaction("👌")

    @bot.command(name = "dl_ctes")
    async def dlCtes(ctx):
        if estAdmin(ctx.author):
            await ctx.send(file = discord.File("constantes.py"))

    @bot.command(name = "update_ctes")
    async def updateCtes(ctx):
        import requests

        if estAdmin(ctx.author) and ctx.message.attachments != []:
            urlNouvConstantes = ctx.message.attachments[0].url

            r = requests.get(urlNouvConstantes)
            with open("constantes.py", "wb") as f:
                f.write(r.content)

            await ctx.message.add_reaction("👌")

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

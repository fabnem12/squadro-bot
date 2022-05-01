import asyncio
import nextcord as discord
import pickle
import os
from nextcord.ext import commands, tasks
from datetime import datetime, timedelta
from random import randint
from typing import Callable, Dict, Optional, Tuple

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import tokenEdt #le token du bot pour se connecter à discord
from utils import cheminOutputs, stockePID
from edtImg import genereEDTNew

stockePID()

cheminPickle = os.path.join(cheminOutputs, "edtbot.p")
ChannelId = int
AgendaId = str
UserId = int

class Agenda:
    def __init__(self, proprio: UserId):
        self.salon: Optional[ChannelId] = None
        self.heure: Optional[int] = None
        self.couleur: Optional[str] = None
        self.url: Optional[str] = None
        self.proprio = proprio

    def __str__(self):
        return f"Agenda dans <#{self.salon}> à {self.heure}h, proprio : <@{self.proprio}>"
    def __repr__(self):
        return str(self)

    def valide(self) -> bool:
        return self.salon is not None and self.heure is not None and self.couleur is not None and self.url is not None

if os.path.exists(cheminPickle):
    try:
        infos: Dict[AgendaId, Agenda] = pickle.load(open(cheminPickle, "rb"))
    except:
        infos: Dict[AgendaId, Agenda] = dict()
else:
    infos: Dict[AgendaId, Agenda] = dict()
    #dictionnaire qui à chaque nom de groupe associe un dictionnaire décrivant :
    # - le salon d'envoi
    # - l'heure d'envoi
    # - la couleur par défaut
    # - l'url Google Agenda

def save():
    pickle.dump(infos, open(cheminPickle, "wb"))

################################################################################

def creeAgenda(proprio: UserId) -> AgendaId: #renvoie l'identifiant hexadécimal du nouvel agenda
    flag = True
    while flag:
        agendaId: AgendaId = hex(randint(1e6, 1e7-1))[2:]
        flag = agendaId in infos #on veut que flag soit faux si l'identifiant n'est pas pris, pour arrêter la boucle

    infos[agendaId] = Agenda(proprio)
    return agendaId

def setSalon(agendaId: AgendaId, salonId: ChannelId) -> bool: #renvoie un booléen décrivant le succès de l'opération
    if agendaId in infos:
        infos[agendaId].salon = salonId
        return True
    return False

def setHeure(agendaId: AgendaId, heure: int) -> bool:
    if agendaId in infos:
        infos[agendaId].heure = heure
        return True
    return False

def setCouleur(agendaId: AgendaId, couleur: str) -> bool:
    if agendaId in infos:
        infos[agendaId].couleur = couleur
        return True
    return False

def setUrl(agendaId: AgendaId, url: str) -> bool:
    if agendaId in infos:
        infos[agendaId].url = url
        save()
        return True
    return False

editMsg: Dict[Tuple[ChannelId, UserId], Tuple[Callable, AgendaId]] = dict() #pour stocker l'état d'edit
async def setAgenda(msg):
    if (msg.channel.id, msg.author.id) in editMsg:
        fonc, agendaId = editMsg[msg.channel.id, msg.author.id]

        if fonc is setHeure:
            if not msg.content.isdigit():
                await msg.channel.send("Euh je n'arrive pas à convertir votre message en nombre…")
                return
            else:
                info = int(msg.content)
        elif fonc is setSalon:
            tronque = msg.content[2:-1]
            if not tronque.isdigit():
                await msg.channel.send("Euh on ne dirait pas une mention de salon…")
                return
            else:
                info = int(tronque)
        else:
            info = msg.content

        succes: bool = fonc(agendaId, info)
        if succes and fonc is not setUrl:
            txt = "C'est noté !\n"
            if fonc is setSalon:
                txt += "À quelle heure faut-il envoyer l'emploi du temps ? Donne-moi juste un entier, j'enverrai l'emploi du temps autour de l'heure pile. À noter que le bot envoie toujours l'emploi du temps du lendemain de l'envoi"
                newFonc = setHeure
            elif fonc is setHeure:
                txt += "De quelle couleur doit être l'emploi du temps ? Il faut un code de couleur hexadécimal (du style #CC00CC, sans oublier le #)"
                newFonc = setCouleur
            elif fonc is setCouleur:
                txt += "Une dernière chose : l'adresse publique iCal de l'agenda (ça doit finir par .ics). Attention, il faut que la case 'Rendre disponible publiquement' dans les paramètres soit bien cochée pour que ça marche."
                newFonc = setUrl
            #else n'est pas possible

            await msg.channel.send(txt)
            editMsg[msg.channel.id, msg.author.id] = (newFonc, agendaId)
        elif fonc is setUrl:
            await msg.channel.send(f"C'est bon, l'agenda est prêt à être envoyé quotidiennement (si l'url a bien été renseignée…). Pour modifier les paramètres d'envoi automatique, il faut supprimer l'agenda avec `A.del {agendaId}` et recréer un envoi automatique avec `A.create`.")
            del editMsg[msg.channel.id, msg.author.id]
        else:
            await msg.channel.send("Euh il y a un problème quelque part :sweat_smile:")

def main():
    bot = commands.Bot(command_prefix="A,", help_command = None)

    @tasks.loop(minutes = 10.0)
    async def envoiEDT():
        from arrow import utcnow
        now = utcnow().to("Europe/Brussels")

        for agenda in infos.values():
            if agenda.valide():
                if (now.hour == agenda.heure and now.minute < 5) or (now.hour == agenda.heure-1 and now.minute >= 55):
                    channel = await bot.fetch_channel(agenda.salon)
                    lienImage, aDesCours = genereEDTNew(agenda.url, agenda.couleur, 1)

                    if aDesCours or now.weekday() not in {4, 5}:
                        await channel.send("Voici l'emploi du temps pour demain :", file = discord.File(lienImage))

    @bot.event
    async def on_ready():
        envoiEDT.start()

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_message(msg):
        await setAgenda(msg)
        await bot.process_commands(msg)

    @bot.command(name = "create")
    async def create(ctx):
        agendaId = creeAgenda(ctx.author.id)
        await ctx.send("Dans quel salon faudra-t-il envoyer l'emploi du temps ? (il faut une mention de salon)")
        editMsg[ctx.channel.id, ctx.author.id] = (setSalon, agendaId)

    @bot.command(name = "edit_color")
    async def editColor(ctx, agendaId: AgendaId, newColor: str):
        if agendaId in infos and infos[agendaId].proprio == ctx.author.id:
            infos[agendaId].couleur = newColor
            save()
            await ctx.message.add_reaction("👌")
        else:
            await ctx.channel.send("https://tenor.com/view/omg-no-stop-please-pleasestop-gif-16120177")

    @bot.command(name = "del")
    async def delete(ctx, agendaId: AgendaId):
        if agendaId in infos and infos[agendaId].proprio == ctx.author.id:
            del infos[agendaId]
            save()
            await ctx.message.add_reaction("👌")
        else:
            await ctx.channel.send("https://tenor.com/view/omg-no-stop-please-pleasestop-gif-16120177")

    @bot.command(name = "renvoi")
    async def renvoi(ctx, agendaId: AgendaId):
        if agendaId in infos:
            agenda = infos[agendaId]
            lienImage, _ = genereEDTNew(agenda.url, agenda.couleur, 1)

            await ctx.channel.send("Voici l'emploi du temps pour demain :", file = discord.File(lienImage))
        else:
            await ctx.message.add_reaction("❔")

    @bot.command(name = "debug")
    async def debug(ctx):
        if ctx.author.id == 619574125622722560:
            await ctx.send(str(infos.items()))

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(tokenEdt))
    loop.run_forever()

main()

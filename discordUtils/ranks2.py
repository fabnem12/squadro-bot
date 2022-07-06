from os.path import join
from arrow import get as arrowGet, utcnow
from random import randint
from time import sleep, time
from typing import Optional, Dict, List, Set, Union, Any, Tuple
import asyncio
import nextcord as discord
import os
import pickle
import numpy as np
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import ADMINS, prefixeBot, TOKENVOLT as TOKEN
from utils import cheminOutputs, stockePID, decoupeMessages
stockePID()

class Member: pass
class Channel: pass
class Server: pass

SERVERS: Dict[int, Server] = dict()

class Server:
    def __init__(self, idServer: int):
        self.id = idServer
        self.channels: Dict[int, Channel] = dict()
        self.members: Dict[int, Member] = dict()
        self.euro = None

    def getMember(self, idDiscord: int) -> Member:
        if idDiscord not in self.members:
            self.members[idDiscord] = Member(idDiscord)
        return self.members[idDiscord]

    def getChannel(self, idChannel: int) -> Channel:
        if idChannel not in self.channels:
            self.channels[idChannel] = Channel(idChannel)
        return self.channels[idChannel]

    def ajoutMsg(self, msg: discord.Message) -> None:
        member = self.getMember(msg.author.id)
        channel = self.getChannel(msg.channel.id)

        temps = arrowGet(msg.created_at.timestamp()).to("Europe/Brussels")
        newXP: int = member.ajoutMsg(temps)

        channel.ajoutMsg(member, temps, newXP)

        if randint(0, 10) < 1: save()

    def ajoutReac(self, reac: discord.Reaction, user: discord.Member) -> None:
        member = self.getMember(user.id)
        channel = self.getChannel(reac.message.channel.id)

        temps = arrowGet(reac.message.created_at.timestamp()).to("Europe/Brussels")
        newXP: int = member.ajoutReac(temps, reac)

        channel.ajoutReac(member, temps, newXP)

    def classement(self, dicoAtrier: Dict[Any, Any], fonctionTri) -> List[Any]:
        return sorted(dicoAtrier.values(), key=fonctionTri, reverse = True)

    def affiClassement(self, dicoAtrier: dict, fonctionTri, fonctionAffi, nbValeurs: int) -> str:
        classementListe = self.classement(dicoAtrier, fonctionTri)

        ret = "__**CLASSEMENT**__\n\n"
        ret += "\n".join(f"**#{i+1}** {fonctionAffi(e)}" for i, e in zip(range(nbValeurs), classementListe))
        return ret

    def affiClassementXP(self, nbTop: int) -> str:
        return self.affiClassement(self.members, lambda x: x.xp(), lambda x: f'<@{x.id}> avec {x.xp()} XP ({x.totalMsgs} messages, {x.totalReacs} réactions)', nbTop)

    def affiClassementMsg(self, nbTop: int) -> str:
        return self.affiClassement(self.members, lambda x: x.totalMsgs, lambda x: f'<@{x.id}> avec {x.totalMsgs} messages ({x.xp()} XP, {x.totalReacs} réactions)', nbTop)

    def eurovision(self, mois: Optional[int] = None, annee: Optional[int] = None) -> Tuple[str, str]:
        #si mois ou annee est None, on fait sur le classement global, sinon sur le mois en question
        parMois = mois is not None and annee is not None
        scores: Dict[Member, int] = dict()

        def affiGlobal() -> str:
            affi = "__**Points donnés**__ : \n\n"
            for member, points in sorted(scores.items(), key=lambda x: x[1], reverse = True):
                affi += f"**{points}** point{'s' if points > 1 else ''}  <@{member.id}>\n"

            return affi[:-1]

        for channel in self.channels.values():
            classementChannel = channel.classementXPMois(mois, annee) if parMois else channel.classementXPGlobal()

            if len(classementChannel) >= 10: #ok on peut faire les points comme à l'eurovision, sinon on laisse tomber ce salon
                pointsChannel = list(zip(classementChannel, (12, 10, 8, 7, 6, 5, 4, 3, 2, 1)))
                affiPointsSalons = f"__**Points dans le salon <#{channel.id}>**__\n"

                for member, points in pointsChannel:
                    affiPointsSalons += f"**{points}** point{'s' if points > 1 else ''}  <@{member.id}>\n"

                    if member not in scores:
                        scores[member] = points
                    else:
                        scores[member] += points

                yield affiGlobal(), affiPointsSalons[:-1]

        self.euro = None

class Member: #on fait un objet member par personne par serveur
    def __init__(self, idDiscord: int):
        self.id = idDiscord
        self.totalMsgs: int = 0
        self.totalReacs: int = 0
        self.msgsParJour: Dict[Tuple[int, int, int], int] = dict() #Tuple[int, int, int] -> (jour, mois, heure)
        self.reacsParJour: Dict[Tuple[int, int, int], int] = dict() #Tuple[int, int, int] -> (jour, mois, heure)
        self.nbParReac: Dict[str, int] = dict() #nb d'utilisations par réaction
        self.dernierEnregistrement = None #identifiant arrow de la minute dernier message / réaction enregistré

        self.xpMsg: int = 0
        self.xpReac: int = 0

    def ajoutMsg(self, temps) -> int: #renvoie le nb d'xps ajoutés
        #on récupère l'heure d'envoi du message dans un format plus précis
        jour = (temps.day, temps.month, temps.year)

        if jour not in self.msgsParJour:
            self.msgsParJour[jour] = 1
        else:
            self.msgsParJour[jour] += 1

        self.totalMsgs += 1
        return self.ajoutXP(temps, True)

    def ajoutReac(self, temps, reaction: discord.Reaction) -> int: #renvoie le nb d'xp ajoutés
        #on récupère l'heure d'envoi de la réaction dans un format plus précis
        jour = (temps.day, temps.month, temps.year)

        if jour not in self.reacsParJour:
            self.reacsParJour[jour] = 1
        else:
            self.reacsParJour[jour] += 1

        self.totalReacs += 1

        if reaction.emoji not in self.nbParReac:
            self.nbParReac[str(reaction.emoji)] = 1
        else:
            self.nbParReac[str(reaction.emoji)] += 1

        return self.ajoutXP(temps, False)

    def ajoutXP(self, temps, estMsg: bool = True) -> int: #temps est un objet créé par arrowGet
        #si estMsg est True, on enregistre un xp de message, sinon c'est un xp de réac
        dernierTps = self.dernierEnregistrement
        if dernierTps is None or (dernierTps.minute != temps.minute or dernierTps.hour != temps.hour or dernierTps.day != temps.day or dernierTps.month != temps.month or dernierTps.year != temps.year):
            newXP: int = round(np.random.normal(20, 5))

            if estMsg: self.xpMsg += newXP
            else: self.xpReac += newXP

            self.dernierEnregistrement = temps
            return newXP
        else:
            return 0

    def xp(self) -> int:
        return self.xpMsg + self.xpReac

class Channel:
    def __init__(self, idChannel: int):
        self.id = idChannel
        self.totalMsgs: int = 0
        self.totalReacs: int = 0
        self.msgsParMember: Dict[Member, Dict[Tuple[int, int, int], int]] = dict() #à chaque member on associe le dictionnaire des jours
        self.reacsParMember: Dict[Member, Dict[Tuple[int, int, int], int]] = dict()
        self.xpParMember: Dict[Member, Dict[Tuple[int, int, int], int]] = dict()

    def ajoutMsg(self, member: Member, temps, newXP: int) -> None:
        if member not in self.msgsParMember:
            self.msgsParMember[member]: Dict[Tuple[int, int, int], int] = dict()
            self.xpParMember[member]: Dict[Tuple[int, int, int], int] = dict()

        jour = (temps.day, temps.month, temps.year)
        if jour not in self.msgsParMember[member]:
            self.msgsParMember[member][jour] = 0
            self.xpParMember[member][jour] = 0

        self.msgsParMember[member][jour] += 1
        self.totalMsgs += 1
        self.xpParMember[member][jour] += newXP

    def ajoutReac(self, member: Member, temps, newXP: int) -> None:
        if member not in self.reacsParMember:
            self.reacsParMember[member]: Dict[Tuple[int, int, int], int] = dict()
        if member not in self.xpParMember:
            self.xpParMember[member]: Dict[Tuple[int, int, int], int] = dict()

        jour = (temps.day, temps.month, temps.year)
        if jour not in self.reacsParMember:
            self.reacsParMember[jour] = 0
        if jour not in self.xpParMember:
            self.xpParMember[jour] = 0

        self.reacsParMember[jour] += 1
        self.totalReacs += 1
        self.xpParMember[jour] += newXP

    def classementXPGlobal(self) -> List[Member]:
        return sorted(self.msgsParMember.keys(), key=lambda x: sum(self.msgsParMember[x].values(), 0), reverse = True)

    def classementXPMois(self, mois: int, annee: int) -> List[Member]:
        return sorted(self.msgsParMember.keys(), key=lambda x: sum((val for (j, m, a), val in self.msgsParMember[x].items() if m==mois and a==annee), 0), reverse = True)

def getServer(idServer: int) -> Server:
    if idServer not in SERVERS:
        SERVERS[idServer] = Server(idServer)
    return SERVERS[idServer]

if "ranksNew.p" in os.listdir(cheminOutputs):
    try:
        SERVERS: Dict[int, Server] = pickle.load(open(join(cheminOutputs, "ranksNew.p"), "rb"))
    except:
        SERVERS = dict()

def save():
    pickle.dump(SERVERS, open(join(cheminOutputs, "ranksNew.p"), "wb"))


def main():
    from nextcord.ext import commands, tasks
    bot = commands.Bot(command_prefix="T.", help_command=None)

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_message(msg):
        server = getServer(msg.guild.id)
        server.ajoutMsg(msg)

        await bot.process_commands(msg)

    @bot.event
    async def on_reaction_add(reaction, user):
        server = getServer(reaction.message.guild.id)
        server.ajoutReac(reaction, user)

    @bot.command(name = "stats")
    async def stats(ctx):
        server = getServer(ctx.guild.id)
        await ctx.send(embed = discord.Embed(description = server.affiClassementXP(20)))

    @bot.command(name = "eurovision")
    async def eurovision(ctx):
        server = getServer(ctx.guild.id)

        if "euro" not in server.__dict__: server.euro = None

        if server.euro is None:
            msgTotal = await ctx.send("Résultats globaux :")
            msgTotal2 = await ctx.send(".")
            msgSalon = await ctx.send(".")
            server.euro = (server.eurovision(), msgTotal.id, msgTotal2.id, msgSalon.id)

        if server.euro:
            iter, tot, tot2, sal = server.euro
            try:
                resGlobaux, resDernierSalon = next(iter)
                resGlobauxNew = decoupeMessages([resGlobaux])
                await (await ctx.channel.fetch_message(tot)).edit(content = "", embed = discord.Embed(description = resGlobauxNew[0]))
                if len(resGlobauxNew) > 1: await (await ctx.channel.fetch_message(tot2)).edit(content = "", embed = discord.Embed(description = resGlobauxNew[1]))
                await (await ctx.channel.fetch_message(sal)).edit(content = "", embed = discord.Embed(description = resDernierSalon))
            except:
                server.euro = None

    @bot.command(name = "prerank")
    async def prerank(ctx):
        if ctx.author.id != 619574125622722560: return

        msgAnnonce = await ctx.send("**Calculs en cours…**")

        if ctx.guild.id in SERVERS:
            del SERVERS[ctx.guild.id]

        server = getServer(ctx.guild.id)

        for channel in ctx.guild.text_channels:
            await msgAnnonce.edit(content = f"**Calculs en cours…**\nLecture de <#{channel.id}>")
            try:
                async for msg in channel.history(limit = None):
                    server.ajoutMsg(msg)
                    for reac in msg.reactions:
                        async for user in reac.users():
                            server.ajoutReac(reac, user)
            except:
                await ctx.send(f"Impossible de lire le salon <#{channel.id}>")

        await msgAnnonce.edit(content = "**Calculs finis !**")

    @bot.command(name = "most_used_emotes")
    async def mostUsedEmotes(ctx):
        if ctx.author.it != 619574125622722560: return

        server = getServer(ctx.guild.id)
        members = server.members

        total = dict()
        for member in members:
            for reac, nb in member.nbParReac.items():
                if reac not in total:
                    total[reac] = 0
                total[reac] += nb

        with open("temp-stats.txt", "w") as f:
            f.write("\n".join(f"{x[0]}: {x[1]}" for x in sorted(total.items(), key=lambda x: x[1], reverse=True)))

        await ctx.send("Result:", file = discord.File("temp-stats.txt"))

        os.remove("temp-stats.txt")

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

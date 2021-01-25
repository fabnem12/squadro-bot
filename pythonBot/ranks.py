from os.path import join
from random import randint
from typing import Optional
import asyncio
import discord
import os
import pickle
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import ADMINS, prefixeBot, TOKEN
from utils import cheminOutputs, stockePID
stockePID()

dossierOutputs = ""

if "ranks.p" not in os.listdir(cheminOutputs):
    infos = dict()
else:
    infos = pickle.load(open(join(cheminOutputs, "ranks.p"), "rb"))

def save():
    pickle.dump(infos, open(join(cheminOutputs, "ranks.p"), "wb"))

def ajoutMsg(guild, author, minute):
    if guild: guild = guild.id #si guild est None, c'est un message privé, sinon c'est un vrai serveur donc on récupère son id

    if guild in infos: infosGuild = infos[guild]
    else:
        infos[guild] = dict()
        infosGuild = infos[guild]

    if author in infosGuild:
        nbPoints, nbMessages, minuteDernier = infosGuild[author]

        if minuteDernier != minute:
            nbPoints += randint(15, 25)

        infosGuild[author] = (nbPoints, nbMessages + 1, minute)
    else:
        nbPoints = randint(15, 25)
        infosGuild[author] = (nbPoints, 1, minute)

    if randint(0, 9) < 1:
        save()

def affiRank(author, guild):
    if guild: guild = guild.id

    if guild in infos:
        infosGuild = infos[guild]

        if author in infosGuild:
            classements = sorted(infosGuild, key = lambda x: infosGuild[x][0], reverse = True)
            rang = classements.index(author)
            nbPoints, nbMessages, _ = infosGuild[author]

            return "<@{}> est {}{} sur ce serveur. {} XPs, {} messages".format(author, rang+1, "e" if rang else "er", nbPoints, nbMessages)
        else:
            return "<@{}> n'as pas envoyé de message sur ce serveur jusque là…".format(author)
    else:
      return "Aucun message n'a été compté sur ce serveur…"

def estAdmin(authorId):
    print(ADMINS, authorId)
    return authorId in ADMINS


def main():
    from discord.ext import commands, tasks
    bot = commands.Bot(command_prefix=prefixeBot, help_command=None)

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    async def affi_stats(guild):
        guildId = guild.id

        infosGuild = infos[guildId]
        classement = sorted(infosGuild, key = lambda x: infosGuild[x][0], reverse = True)

        txt = "**Personnes les plus actives sur le serveur :**\n"
        for index, usrId in enumerate(classement):
            usr = await guild.fetch_member(usrId)
            nbPoints, nbMessages, _ = infosGuild[usrId]

            txt += "**{}** {} avec {} XP ({} messages)\n".format(index+1, usr.nick or usr.name, nbPoints, nbMessages)
            if index == 19: break

        return txt

    @bot.event
    async def on_message(msg):
        author = msg.author.id
        minute = msg.created_at.timestamp() // 60
        guild = msg.guild
        ajoutMsg(guild, author, minute)

        await bot.process_commands(msg)

    @bot.command(name="prerank")
    async def prerank(ctx):
        if not estAdmin(ctx.author.id): return

        msgAnnonce = await ctx.send("**Calculs en cours…**")

        for channel in ctx.guild.text_channels:
             await msgAnnonce.edit(content = "**Calculs en cours…**\nSalon {} en cours de revue…".format(channel.name))

             try:
                 async for message in channel.history(limit = None):
                     ajoutMsg(message.guild, message.author.id, message.created_at.timestamp() // 60)
             except:
                 print("Erreur : ", channel.name)

        await msgAnnonce.edit(content = "**Calculs finis !**")
        save()

    @bot.command(name = "rank")
    async def rank(ctx, someone: Optional[discord.Member]):
        if someone is None: someone = ctx.author.id
        else: someone = someone.id #int(someone[3:21])

        await ctx.send(affiRank(someone, ctx.guild))

    @bot.command(name = "stats")
    async def stats(ctx):
        res = await affi_stats(ctx.guild)
        await ctx.send(res)

    return bot, TOKEN

if __name__ == "__main__": #pour lancer le bot
    bot, token = main()

    bot.run(token)

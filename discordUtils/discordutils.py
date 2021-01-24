import asyncio
import discord
import os
import pickle
import requests
import sys
from discord.ext import commands
from time import sleep

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID, cheminOutputs

stockePID()

#on récupère les constantes dans le pickle
cheminPickle = os.path.join(cheminOutputs, "discordutils.p")
if not os.path.exists(cheminPickle):
    pickle.dump({"BINDED_CHANNELS": dict()}, open(cheminPickle, "wb"))

INFOS = pickle.load(open(cheminPickle, "rb"))
BINDED_CHANNELS = INFOS["BINDED_CHANNELS"]
MSG_RETRANSMIS = dict()
ECHO2MSG = dict()

def save():
    pickle.dump(INFOS, open(cheminPickle, "wb"))

def estAdmin(usrId): return usrId in ADMINS

def resendFile(url, nomFichier):
    cheminSave = os.path.join(cheminOutputs, nomFichier)
    r = requests.get(url)
    with open(cheminSave, "wb") as f:
        f.write(r.content)

    return discord.File(cheminSave)

def supprFichier(fichierDiscord):
    chemin = os.path.join(cheminOutputs, fichierDiscord.filename)
    os.remove(chemin)
################################################################################

async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm() #crée le dm channel, et après user.dm_channel est remplacé par l'objet représentant le dm channel
    return user.dm_channel

async def bind_channel_envoi(msg):
    if msg.author.id == bot.user.id: return

    if msg.channel.id in BINDED_CHANNELS:
        auteur, texte, files = msg.author, msg.content, [resendFile(x.url, x.filename) for x in msg.attachments]
        reference = msg.reference

        texteRenvoye = "**@{} :**\n{}".format(auteur.nick or auteur.name, texte)

        MSG_RETRANSMIS[msg.id] = (auteur, dict(), msg)

        for serveurCible, salonCible in BINDED_CHANNELS[msg.channel.id]:
            serveur = bot.get_guild(serveurCible)
            channel = serveur.get_channel(salonCible)

            if reference:
                refId = reference.message_id
                #il y a deux cas
                #1. soit on fait référence à un "vrai" message qui a été retransmis
                #2. soit on fait référence à un écho

                #1.
                if refId in MSG_RETRANSMIS:
                    refEcho = MSG_RETRANSMIS[refId][1][salonCible].id
                    chanRef = channel.id
                #2.
                elif refId in ECHO2MSG:
                    refEcho, _ = ECHO2MSG[refId]
                    chanRef = channel.id

                objRef = discord.MessageReference(message_id = refEcho, channel_id = chanRef)
                retransmis = await channel.send(texteRenvoye, reference = objRef, files = files)
            else:
                retransmis = await channel.send(texteRenvoye, files = files)

            MSG_RETRANSMIS[msg.id][1][salonCible] = retransmis
            ECHO2MSG[retransmis.id] = (msg.id, msg.channel.id)
            sleep(0.5)

            for x in files: supprFichier(x)

async def bind_channel_edit(msg):
    if msg.id in MSG_RETRANSMIS:
        texte, embeds = msg.content, msg.embeds
        auteur, echos, _ = MSG_RETRANSMIS[msg.id]

        texteRenvoye = "**@{} :**\n{}".format(auteur.nick or auteur.name, texte)

        for echo in echos.values():
            await echo.edit(content = texteRenvoye)

async def bind_channel_del(msg):
    if msg.id in MSG_RETRANSMIS:
        for echo in MSG_RETRANSMIS[msg.id][1].values():
            await echo.delete()

async def bind_channel_react_add(reaction, user, bot):
    compte = reaction.count
    msgId = reaction.message.id

    if user.id == bot.user.id: return

    if compte:
        #1. on a fait une réaction sur un écho, on ajoute la réaction sur le message de départ
        if msgId in ECHO2MSG:
            print(1)
            msgId, channelId = ECHO2MSG[msgId]
            channel = await bot.fetch_channel(channelId)
            msg = await channel.fetch_message(msgId)

            await msg.add_reaction(reaction.emoji)
        #2.
        elif msgId in MSG_RETRANSMIS:
            print(2)
            _, echos, _ = MSG_RETRANSMIS[msgId]

            for echo in echos.values():
                await echo.add_reaction(reaction.emoji)

def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None)

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_message_edit(_, msg):
        await bind_channel_edit(msg)

    @bot.event
    async def on_message_delete(msg):
        await bind_channel_del(msg)

    @bot.event
    async def on_reaction_add(reaction, user):
        await bind_channel_react_add(reaction, user, bot)

    @bot.event
    async def on_message(msg):
        #liaison de salon
        await bind_channel_envoi(msg)

        await bot.process_commands(msg)

    #bind channels
    @bot.command(name = "utils_bind")
    async def bind(ctx, salonSource: int, serveurCible: int, salonCible: int):
        if not estAdmin(ctx.author.id): return

        serveurSource = ctx.guild.id

        if salonSource in BINDED_CHANNELS:
            cible = BINDED_CHANNELS[salonSource]
        else:
            cible = set()
            BINDED_CHANNELS[salonSource] = cible

        cible.add((serveurCible, salonCible))

        if salonCible in BINDED_CHANNELS:
            cible = BINDED_CHANNELS[salonCible]
        else:
            cible = set()
            BINDED_CHANNELS[salonCible] = cible

        cible.add((serveurSource, salonSource))

        confirmation = await ctx.send("OK")
        save()

    @bot.command(name = "utils_unbind")
    async def unbind(ctx, salonSource: int):
        if not estAdmin(ctx.author.id): return

        if salonSource in BINDED_CHANNELS:
            for (_, channel) in BINDED_CHANNELS[salonSource]:
                BINDED_CHANNELS[channel] = {(x, y) for x, y in BINDED_CHANNELS[channel] if y != salonSource}

            BINDED_CHANNELS[salonSource] = set()
            await ctx.send("OK")
        else:
            await ctx.send("Ce salon n'était pas relié aux autres")

        save()

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

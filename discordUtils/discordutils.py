import asyncio
import discord
import os
import pickle
import requests
import sys
from discord.ext import commands
from random import randint
from time import sleep
from typing import Optional, Union, Dict, Set, Tuple
try:
    from open_digraph import *
except ImportError:
    from .open_digraph import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONSTANTES ###################################################################
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID, cheminOutputs
ChannelID = Tuple[int, int] #tuple qui contient l'id du salon et l'id du serveur
Message = int #l'id du message
class Groupe(OpenDigraph):
    def __init__(self):
        super().__init__([], [], [])
        self.originaux: Dict[Message, Message] = dict() #associe à une copie le message original
        self.copies: Dict[Message, Set[Message]] = dict() #associe à un original la liste de ses copies
        self.copiesGuild: Dict[Tuple[Message, ChannelID], Message] = dict() #associe à un message son pendant sur un autre salon
        self.auteur: Dict[Message, str] = dict() #associe à un message le pseudo de son auteur

    def salonInGroupe(self: 'Groupe', channelId: ChannelID) -> bool:
        return any(x.getLabel() == channelId for x in self.getNodes())
    def getNodeChannel(self: 'Groupe', channelId: ChannelID) -> Optional[Node]:
        for node in self.getNodes():
            if node.getLabel() == channelId:
                return node

    def autresSalons(self: 'Groupe', channelId: ChannelID) -> Set[ChannelID]:
        nodeChannel = self.getNodeChannel(channelId)
        return {self.nodes[idChild].getLabel() for idChild in nodeChannel.getChildrenIds()}

    def ajoutMsg(self: 'Groupe', idOriginal: Message, idCopie: Message, channelIdOriginal: ChannelID, channelIdCopie: ChannelID, auteur: str) -> None:
        self.originaux[idCopie] = (idOriginal, channelIdOriginal)
        self.copiesGuild[idCopie, channelIdOriginal] = idOriginal
        self.copiesGuild[idOriginal, channelIdCopie] = idCopie
        self.auteur[idOriginal] = auteur
        self.auteur[idCopie] = auteur

        if idOriginal not in self.copies:
            self.copies[idOriginal] = {(idCopie, channelIdCopie)}
        else:
            self.copies[idOriginal].add((idCopie, channelIdCopie))

    def copiesMessage(self: 'Groupe', idMsg: Message) -> Set[Tuple[Message, ChannelID]]:
        if idMsg in self.copies: #idMsg est un message original, c'est facile de retrouver ses copies
            return self.copies[idMsg]
        else: #idMsg est une copie par le bot, il faut retrouver l'original et les copies de l'original - idMsg
            original = self.originaux[idMsg]
            return {original} | {x for x in self.copies[original] if x[0] != idMsg}
    def copieDansSalon(self: 'Groupe', idMsg: Message, channelId: ChannelID) -> Optional[Message]:
        if (idMsg, channelId) in self.copiesGuild: #ça ne marche que si idMsg est le message original
            return self.copiesGuild[idMsg, channelId]
        else: #sinon, il faut retrouver l'original
            msgOriginal, channelOriginal = self.originaux[idMsg]
            #par construction le truc suivant existe forcément
            return self.copiesGuild[msgOriginal, channelId]
    def auteurMsg(self: 'Groupe', idMsg: Message) -> str:
        return self.auteur[idMsg]

stockePID()

#on récupère les constantes dans le pickle
cheminPickle = os.path.join(cheminOutputs, "discordutils.p")

try:
    INFOS = dict() if not os.path.exists(cheminPickle) else pickle.load(open(cheminPickle, "rb"))
except:
    INFOS = dict()

if True:
    if "BINDED_CHANNELS" not in INFOS: INFOS["BINDED_CHANNELS"] = dict()
    BINDED_CHANNELS = INFOS["BINDED_CHANNELS"]
    MSG_RETRANSMIS = dict()
    ECHO2MSG = dict()
    BLANK = "‎" * 3

    if "VOCAL_ROLE" not in INFOS: INFOS["VOCAL_ROLE"] = dict()
    VOCAL_ROLE = INFOS["VOCAL_ROLE"]

    if "AUTO_ROLE" not in INFOS: INFOS["AUTO_ROLE"] = dict()
    AUTO_ROLE = INFOS["VOCAL_ROLE"]

    if "BIND_NEW" not in INFOS: INFOS["BIND_NEW"] = dict()
    BIND_NEW = INFOS["BIND_NEW"]

    if "AUTO_ASSO" not in INFOS: INFOS["AUTO_ASSO"] = dict()
    AUTO_ASSO = INFOS["AUTO_ASSO"]

    if "AUTO_ROLE_CONF" not in INFOS: INFOS["AUTO_ROLE_CONF"] = dict()
    AUTO_ROLE_CONF = INFOS["AUTO_ROLE_CONF"]

    if "AUTO_PINS" not in INFOS: INFOS["AUTO_PINS"] = dict()
    AUTO_PINS = INFOS["AUTO_PINS"]

    if "CLOSE" not in INFOS: INFOS["CLOSE"] = set()
    CLOSE = INFOS["CLOSE"]

    if "MODO" not in INFOS: INFOS["MODO"] = {753312911274934345: 193233316391026697, 690209463369859129: 619574125622722560}
    MODO = INFOS["MODO"]

def save():
    pickle.dump(INFOS, open(cheminPickle, "wb"))

def estAdmin(usrId): return usrId in ADMINS


#TRUCS UTILES ##################################################################
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
    if msg.content.startswith(BLANK): return

    if msg.channel.id in BINDED_CHANNELS:
        auteur, texte, files = msg.author, msg.content, [resendFile(x.url, x.filename) for x in msg.attachments]
        embeds = msg.embeds
        reference = msg.reference
        pseudoAuteur = auteur.nick or auteur.name

        embed = None if embeds == [] or auteur.id != bot.user.id else embeds[0]

        texteRenvoye = BLANK + "**@{} ({}) :**\n{}".format(pseudoAuteur, msg.guild.name if msg.guild else "DM", texte)

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
                retransmis = await channel.send(texteRenvoye, reference = objRef, files = files, embed = embed)
            else:
                retransmis = await channel.send(texteRenvoye, files = files, embed = embed)

            MSG_RETRANSMIS[msg.id][1][salonCible] = retransmis
            ECHO2MSG[retransmis.id] = (msg.id, msg.channel.id)
            sleep(0.5)

        for x in files: supprFichier(x)

async def bind_new_envoi(msg):
    if msg.content.startswith(BLANK): return
    channelId = msg.channel.id
    guildId = msg.guild.id if msg.guild else msg.guild


    if channelId in BIND_NEW:
        if msg.content == "" and msg.embeds == [] and msg.attachments == []: return #c'est un message système qu'on ne veut pas transmettre

        groupe = BIND_NEW[BIND_NEW[channelId]]
        auteur, texte, files = msg.author, msg.content, lambda: [resendFile(x.url, x.filename) for x in msg.attachments]
        embeds = msg.embeds
        reference = msg.reference
        pseudoAuteur = auteur.nick or auteur.name

        embed = None if embeds == [] or auteur.id != bot.user.id else embeds[0]
        texteRenvoye = BLANK + "**@{} ({}) :**\n{}".format(pseudoAuteur, msg.guild.name if msg.guild else "DM", texte)

        for channelCibleId, serveurCibleId in groupe.autresSalons((channelId, guildId)):
            serveur = bot.get_guild(serveurCibleId)
            channel = serveur.get_channel(channelCibleId)
            fichiersHere = files()

            if reference:
                referenceId = reference.message_id
                pendantRefChannel = groupe.copieDansSalon(referenceId, (channelCibleId, serveurCibleId))
                objRef = discord.MessageReference(message_id = pendantRefChannel, channel_id = channelCibleId)
                retransmis = await channel.send(texteRenvoye, reference = objRef, files = fichiersHere, embed = embed)
            else:
                retransmis = await channel.send(texteRenvoye, files = fichiersHere, embed = embed)

            groupe.ajoutMsg(msg.id, retransmis.id, (channelId, guildId), (channelCibleId, serveurCibleId), pseudoAuteur)

            map(supprFichier, fichiersHere)
            sleep(0.4)

    if randint(0, 10) == 0: save()

async def bind_channel_edit(msg):
    if msg.id in MSG_RETRANSMIS:
        texte, embeds = msg.content, msg.embeds
        auteur, echos, _ = MSG_RETRANSMIS[msg.id]

        texteRenvoye = BLANK + "**@{} ({}) :**\n{}".format(auteur.nick or auteur.name, msg.guild.name if msg.guild else "DM", texte)

        for echo in echos.values():
            await echo.edit(content = texteRenvoye)

async def bind_new_edit(msg):
    channelId = msg.channel.id
    guildId = msg.guild.id if msg.guild else msg.guild
    if msg.author.id == 689536409060900933: return #on ne fait rien si le bot modifie son propre message

    if channelId in BIND_NEW:
        groupe = BIND_NEW[BIND_NEW[channelId]]
        texte, embeds = msg.content, msg.embeds
        pseudoAuteur = groupe.auteurMsg(msg.id)

        texteRenvoye = BLANK + "**@{} ({}) :**\n{}".format(pseudoAuteur, msg.guild.name if msg.guild else "DM", texte)
        for channelCibleId, serveurCibleId in groupe.autresSalons((channelId, guildId)):
            serveur = bot.get_guild(serveurCibleId)
            channel = serveur.get_channel(channelCibleId)

            echoId = groupe.copieDansSalon(msg.id, (channelCibleId, serveurCibleId))
            echo = await channel.fetch_message(echoId)
            await echo.edit(content = texteRenvoye)

async def bind_channel_del(msg):
    msgInit = msg.id
    if msg.id in ECHO2MSG: #si c'est un écho, on retrouve le message original pour retrouver les autres échos
        msgInit = ECHO2MSG[msg.id][0]
        del MSG_RETRANSMIS[msgInit][1][msg.channel.id] #on a supprimé cet écho donc on le retire de MSG_RETRANSMIS

        #on peut tenter de supprimer le message original (mais ce n'est pas garanti, le bot peut ne pas avoir les droits)
        try:
            await MSG_RETRANSMIS[msgInit][2].delete()
        except: pass #on ne fait rien si la suppression de l'original n'a pas marché

    if msgInit in MSG_RETRANSMIS:
        for echo in MSG_RETRANSMIS[msgInit][1].values():
            await echo.delete()

async def bind_new_del(msg):
    channelId = msg.channel.id
    guildId = msg.guild.id if msg.guild else msg.guild

    if channelId in BIND_NEW:
        groupe = BIND_NEW[BIND_NEW[channelId]]

        for channelCibleId, serveurCibleId in groupe.autresSalons((channelId, guildId)):
            try:
                serveur = bot.get_guild(serveurCibleId)
                channel = serveur.get_channel(channelCibleId)

                echoId = groupe.copieDansSalon(msg.id, (channelCibleId, serveurCibleId))
                echo = await channel.fetch_message(echoId)
                await echo.delete()
                sleep(0.4)
            except:
                print("Mon développeur a triché !")

async def bind_channel_react_add(reaction, user, bot):
    compte = reaction.count
    msgId = reaction.message.id

    if user.id == bot.user.id: return

    if compte:
        #1. on a fait une réaction sur un écho, on ajoute la réaction sur le message initial
        #et les autres échos via la partie 2
        if msgId in ECHO2MSG:
            msgId, channelId = ECHO2MSG[msgId] #msgId désignera désormais le message initial
            channel = await bot.fetch_channel(channelId)
            msg = await channel.fetch_message(msgId)

            await msg.add_reaction(reaction.emoji)
            sleep(0.5)
        #2.
        if msgId in MSG_RETRANSMIS:
            _, echos, _ = MSG_RETRANSMIS[msgId]

            for echo in echos.values():
                await echo.add_reaction(reaction.emoji)
                sleep(0.5)

async def bind_new_react_add(reaction, user, bot):
    msg = reaction.message
    channelId = msg.channel.id
    guildId = msg.guild.id

    if channelId in BIND_NEW:
        groupe = BIND_NEW[BIND_NEW[channelId]]

        for channelCibleId, serveurCibleId in groupe.autresSalons((channelId, guildId)):
            serveur = bot.get_guild(serveurCibleId)
            channel = serveur.get_channel(channelCibleId)

            echoId = groupe.copieDansSalon(msg.id, (channelCibleId, serveurCibleId))
            echo = await channel.fetch_message(echoId)
            await echo.add_reaction(reaction.emoji)
            sleep(0.4)

async def bind_channel_react_del(reaction, bot):
    msgId = reaction.message.id

    if True:
        #1. on a retiré une réaction sur un écho, on retire la réaction du bot sur l'original
        if msgId in ECHO2MSG:
            msgId, channelId = ECHO2MSG[msgId]
            channel = await bot.fetch_channel(channelId)
            msg = await channel.fetch_message(msgId)

            await msg.remove_reaction(reaction.emoji, bot.user)
        #2.
        elif msgId in MSG_RETRANSMIS:
            _, echos, _ = MSG_RETRANSMIS[msgId]

            for echo in echos.values():
                await echo.remove_reaction(reaction.emoji, bot.user)

async def bind_new_react_del(reaction, bot):
    pass

async def bind_new_pin_event(channel, last_pin):
    channelId = channel.id
    guildId = channel.guild.id

    if last_pin and channelId in BIND_NEW: #sinon, c'est qu'on a retiré un pin (et pour le moment on ne fait rien)
        lastPinMsg = (await channel.pins())[0]
        groupe = BIND_NEW[BIND_NEW[channelId]]

        for channelCibleId, serveurCibleId in groupe.autresSalons((channelId, guildId)):
            serveur = bot.get_guild(serveurCibleId)
            channel = serveur.get_channel(channelCibleId)

            echoId = groupe.copieDansSalon(lastPinMsg.id, (channelCibleId, serveurCibleId))
            echo = await channel.fetch_message(echoId)
            try:
                await echo.pin()
            except:
                print("Mon développeur a triché")
            sleep(0.4)

async def vocalrole_voicestate(member, before, after):
    channelBefore = before.channel and before.channel.id
    #si before.channel est None, il reste None, sinon on prend directement l'id du channel
    channelAfter = after.channel and after.channel.id
    guild = member.guild

    if guild.id in VOCAL_ROLE:
        rolesGuild = VOCAL_ROLE[guild.id]

        if channelBefore in rolesGuild and (channelAfter not in rolesGuild or (channelAfter in rolesGuild and rolesGuild[channelBefore] != rolesGuild[channelAfter])):
            retraitRole = guild.get_role(rolesGuild[channelBefore])
            await member.remove_roles(retraitRole)

        if channelAfter in rolesGuild and (channelBefore not in rolesGuild or (channelBefore in rolesGuild and rolesGuild[channelBefore] != rolesGuild[channelAfter])):
            nouvRole = guild.get_role(rolesGuild[channelAfter])
            await member.add_roles(nouvRole)

async def autorole_react_add(messageId, member, guild, emoji, add = True):
    if (messageId, emoji) in AUTO_ROLE:
        roleId = AUTO_ROLE[messageId, emoji]
        role = guild.get_role(roleId)

        if add and role not in member.roles:
            await member.add_roles(role)
        elif not add and role in member.roles:
            await member.remove_roles(role)

async def autorole_react_del(messageId, member, guild, emoji):
    await autopin_react_add(messageId, member, guild, emoji, False)

async def autoroleconf_react_add(messageId, member, guild, emoji):
    if (messageId, emoji) in AUTO_ROLE_CONF:
        roleId, channelConfId, pingConfId, serveurAutoId, roleAutoId, toWhoId = AUTO_ROLE_CONF[messageId, emoji]
        role = guild.get_role(roleId)

        dm = await dmChannelUser(member)

        roleConfirme = toWhoId is not None
        if serveurAutoId is not None:
            serveurAuto = bot.get_guild(serveurAutoId)
            roleAuto = serveurAuto.get_role(roleAutoId)

            memberAutreServeur = await serveurAuto.fetch_member(member.id)
            roleConfirme = memberAutreServeur and roleAuto in memberAutreServeur.roles

        if roleConfirme:
            if toWhoId:
                member = await guild.fetch_member(toWhoId)
                dm = await dmChannelUser(member)

            await member.add_roles(role)
            await dm.send("**__Arrivée sur le serveur de TD de L2 MPI__**\nC'est bon, ton groupe de TD est confirmé !\nAu fait, ce serait bien si tu pouvais prendre sur ce serveur un pseudo qui permettrait à tes profs de t'identifier x).")

            if toWhoId:
                del AUTO_ROLE_CONF[messageId, emoji]

                save()
        else:
            channelConf = guild.get_channel(channelConfId)

            msgConf = await channelConf.send(f"<@&{pingConfId}> : {member.mention} prétend être du groupe {role.name}. C'est vrai ?")
            await msgConf.add_reaction("👍")

            AUTO_ROLE_CONF[msgConf.id, "👍"] = (roleId, channelConfId, pingConfId, serveurAutoId, roleAutoId, member.id)

            save()

            await dm.send(f"**__Arrivée sur le serveur de TD de L2 MPI__**\nBienvenue sur le serveur ! Tu as dit être dans le groupe {role.name}, ce sera confirmé par les admins bientôt.")

async def autoasso_react_add(messageId, member, guild, emoji):
    messagesVerifies = (813413525560361010, 813413830918406224) #questions entrée
    messageAcces = 820709722860027915
    roleMembreServeurAsso = 811670434315239424
    memberId = member.id

    if messageId in messagesVerifies: #on répond à une question du "qcm" d'entrée, on enregistre la question à laquelle le membre a répondu
        if memberId in AUTO_ASSO:
            AUTO_ASSO[memberId].add(messageId)
        else:
            AUTO_ASSO[memberId] = {messageId}

        save()

    elif messageId == messageAcces: #on demande l'accès en acceptant le règlement
        if memberId not in AUTO_ASSO or len(AUTO_ASSO[memberId]) != len(messagesVerifies): #le qcm n'a pas été répondu
            channel = await dmChannelUser(member)

            await channel.send(f"**Arrivée sur le serveur de l'API des Passionnés d'Informatique**\nMerci d'avoir rejoint le serveur ! Pour y avoir accès, svp mettez bien des réactions aux {len(messagesVerifies)} messages au-dessus de celui qui permet d'accepter le règlement, puis remettre la réaction pour accepter le règlement.\nÀ bientôt !")
        else: #le qcm a été répondu, on donne l'accès au reste du serveur
            role = guild.get_role(roleMembreServeurAsso)
            await member.add_roles(role)

async def autopin_react_add(messageId, member, guild, emoji, channel):
    if emoji == "📌": #c'est un pin !
        if messageId not in AUTO_PINS:
            AUTO_PINS[messageId] = {member.id}
        else:
            AUTO_PINS[messageId].add(member.id)

        save()

        if len(AUTO_PINS[messageId]) == 5: #on a 5 personnes qui demandent un pin, on le fait
            msg = await channel.fetch_message(messageId)

            try:
                await msg.pin()
            except:
                await channel.send("Le bot n'a pas le droit d'épingler des messages ici")

async def autopin_react_del(messageId, member, guild, emoji, channel):
    if emoji == "📌":
        if messageId in AUTO_PINS:
            AUTO_PINS[messageId].remove(member.id)

            save()

            if len(AUTO_PINS[messageId]) < 5:
                msg = await channel.fetch_message(messageId)

                try:
                    await msg.unpin()
                except:
                    pass

async def envoiAutoSuppr(msg):
    if msg.guild and msg.guild.id in MODO:
        channel = await bot.fetch_user(MODO[msg.guild.id])
        await channel.send(f"{str(msg.created_at)} - {str(msg.channel.name)} - {msg.author.nick or msg.author.name} : {msg.content}")

async def close_envoi(msg):
    channelId = msg.channel.id
    if channelId in CLOSE:
        try:
            await msg.delete()
        except:
            pass

def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None, intents = discord.Intents.all())

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    @bot.event
    async def on_message_edit(_, msg):
        await bind_channel_edit(msg)
        await bind_new_edit(msg)

    @bot.event
    async def on_message_delete(msg):
        await bind_channel_del(msg)
        await bind_new_del(msg)
        await envoiAutoSuppr(msg)

    @bot.event
    async def on_member_join(member):
        bans = []
        for guild in bot.guilds:
            try:
                bans += list(x.user.id for x in (await guild.bans()))
            except: pass

        try:
            if member.id in bans:
                await member.ban()
        except:
            pass

    async def traitementRawReact(payload):
        if payload.guild_id and payload.user_id != bot.user.id: #sinon, on est dans le cas d'une réaction en dm
            messageId = payload.message_id
            guild = bot.get_guild(payload.guild_id)
            user = await guild.fetch_member(payload.user_id)
            channel = await bot.fetch_channel(payload.channel_id)

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

            await autorole_react_add(messageId, user, guild, emojiHash)
            await autoasso_react_add(messageId, user, guild, emojiHash)
            await autoroleconf_react_add(messageId, user, guild, emojiHash)
            await autopin_react_add(messageId, user, guild, emojiHash, channel)

    @bot.event
    async def on_raw_reaction_remove(payload):
        traitement = await traitementRawReact(payload)
        if traitement:
            messageId = traitement["messageId"]
            user = traitement["user"]
            guild = traitement["guild"]
            emojiHash = traitement["emojiHash"]
            channel = traitement["channel"]

            await autorole_react_del(messageId, user, guild, emojiHash)
            await autopin_react_del(messageId, user, guild, emojiHash, channel)

    @bot.event
    async def on_reaction_add(reaction, user):
        await bind_channel_react_add(reaction, user, bot)
        await bind_new_react_add(reaction, user, bot)
    @bot.event
    async def on_reaction_clear_emoji(reaction):
        await bind_channel_react_del(reaction, bot)
        await bind_new_react_del(reaction, bot)

    @bot.event
    async def on_voice_state_update(member, before, after):
        await vocalrole_voicestate(member, before, after)


    @bot.event
    async def on_message(msg):
        #liaison de salon
        await bind_channel_envoi(msg)
        await bind_new_envoi(msg)
        await bot.process_commands(msg)
        await close_envoi(msg)

    @bot.event
    async def on_guild_channel_pins_update(channel, last_pin):
        await bind_new_pin_event(channel, last_pin)

    #bind channels
    @bot.command(name = "utils_bind")
    async def bind(ctx, salonSource: discord.TextChannel, serveurCible: int, salonCible: int):
        if not estAdmin(ctx.author.id): return

        salonSource = salonSource.id
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

        await ctx.message.add_reaction("👌")

        save()

    @bot.command(name = "utils_unbind")
    async def unbind(ctx, salonSource: discord.TextChannel):
        if not estAdmin(ctx.author.id): return

        salonSource = salonSource.id

        if salonSource in BINDED_CHANNELS:
            for (_, channel) in BINDED_CHANNELS[salonSource]:
                BINDED_CHANNELS[channel] = {(x, y) for x, y in BINDED_CHANNELS[channel] if y != salonSource}

            BINDED_CHANNELS[salonSource] = set()
            await ctx.message.add_reaction("👌")
        else:
            await ctx.send("Ce salon n'était pas relié aux autres")

        save()

    #bind new
    @bot.command(name = "create_bind")
    async def createBind(ctx):
        int_to_hex = lambda x: hex(x)[2:]
        idGroupe = int_to_hex(randint(1000000, 9999999))
        BIND_NEW[idGroupe] = Groupe()

        await ctx.send(f"Id du groupe : {idGroupe}. Pour ajouter un nouveau salon, il faut lancer la commande `{prefixeBot}bind {idGroupe}`")

        save()

    @bot.command(name = "bind")
    async def bindnew(ctx, nomGroupe: str):
        channelId = ctx.channel.id
        guildId = ctx.guild.id if ctx.guild else ctx.guild

        if nomGroupe in BIND_NEW:
            groupe = BIND_NEW[nomGroupe]
            if groupe.salonInGroupe((channelId, guildId)):
                await ctx.message.add_reaction("❔")
            else:
                autresNodes = groupe.getNodeIds()
                groupe.addNode((channelId, guildId), autresNodes, autresNodes)
                BIND_NEW[channelId] = nomGroupe

                await ctx.message.add_reaction("👌")
                save()
        else:
            await ctx.message.add_reaction("❌")

    @bot.command(name = "del_bind")
    async def delBind(ctx, nomGroupe: str):
        if nomGroupe in BIND_NEW:
            for node in BIND_NEW[nomGroupe].getNodes():
                channelId, guildId = node.getLabel()
                del BIND_NEW[channelId]

            del BIND_NEW[nomGroupe]
            await ctx.message.add_reaction("👌")

            save()
        else:
            await ctx.message.add_reaction("❔")

    #vocal role
    @bot.command(name = "utils_vocalbind")
    async def vocalbind(ctx, role: discord.Role, salonVocalId: int):
        if not estAdmin(ctx.author.id): return

        guildId = role.guild.id

        if guildId not in VOCAL_ROLE:
            VOCAL_ROLE[guildId] = dict()

        VOCAL_ROLE[guildId][salonVocalId] = role.id
        await ctx.message.add_reaction("👌")

        save()

    @bot.command(name = "utils_vocalunbind")
    async def vocalunbind(ctx, role: discord.Role):
        if not estAdmin(ctx.author.id): return

        guildId = role.guild.id
        roleId = role.id

        if guildId in VOCAL_ROLE:
            if roleId in VOCAL_ROLE[guildId].values():
                for salon in (x for x, y in VOCAL_ROLE.items() if y == roleId):
                    del VOCAL_ROLE[guildId][roleId]

                await ctx.message.add_reaction("👌")

                save()
                return

        await ctx.send("Inutile")

    #autorole
    @bot.command(name = "utils_autorole")
    async def autorole(ctx, role: discord.Role, message: discord.Message, emoji: Union[discord.Emoji, str]):
        emojiHash = emoji.id if isinstance(emoji, discord.Emoji) else emoji
        messageId = message.id

        if (messageId, emojiHash) not in AUTO_ROLE:
            AUTO_ROLE[messageId, emojiHash] = role.id

            try:
                await message.add_reaction(emoji)
            except:
                pass
            await ctx.send("Autorole activé")
        else:
            del AUTO_ROLE[messageId, emojiHash]
            await ctx.send("Autorole désactivé")

            try:
                await message.remove_reaction(emoji, bot.user)
            except:
                pass

        save()

    #autorole avec confirmation (sauf reconnaissance automatique)
    @bot.command(name = "utils_autoroleconf")
    async def autoroleconf(ctx, role: discord.Role, message: discord.Message, emoji: Union[discord.Emoji, str], channelConf: discord.TextChannel, pingConf: discord.Role, serveurAutoId: Optional[int], roleAutoId: Optional[int]):
        emojiHash = emoji.id if isinstance(emoji, discord.Emoji) else emoji
        messageId = message.id

        AUTO_ROLE_CONF[messageId, emojiHash] = (role.id, channelConf.id, pingConf.id, serveurAutoId, roleAutoId, None)

        try:
            await message.add_reaction(emoji)
            await ctx.message.add_reaction("👌")
        except:
            pass

        save()

    @bot.command(name = "utils_autoroleconf_reset")
    async def autoroleconfreset(ctx):
        AUTO_ROLE_CONF.clear()
        await ctx.message.add_reaction("👌")

        save()

    @bot.command(name = "open")
    async def open(ctx):
        CLOSE.remove(ctx.channel.id)
        save()
        await ctx.message.add_reaction("👌")

    @bot.command(name = "close")
    async def close(ctx):
        CLOSE.add(ctx.channel.id)
        save()
        await ctx.message.add_reaction("👌")

    @bot.command(name="toto")
    async def toto(ctx, channelId: int = 753333174364274768):
        channelAdmin = await bot.fetch_channel(channelId)

        txt = ""
        i = 0
        async for msg in channelAdmin.history(limit = 1000):
            if i % 100 == 0: print(i)
            i += 1
            txt += f"{str(msg.created_at)} - {msg.author.nick or msg.author.name} : {msg.content}\n"
            print(f"{str(msg.created_at)} - {msg.author.nick or msg.author.name} : {msg.content}\n")

        with open("res.txt", "w") as f:
            f.write(txt)

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

import asyncio
import discord
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constantes import prefixeBot, TOKEN
from utils import stockePID
from libvote import Votant, Election

stockePID()

ELECTIONS = dict() #associe à un identifiant d'élection un tuple : l'objet Election correspondant, et l'id discord de la personne qui l'a lancée
MSG2DUEL = dict() #associe un message à un duel (objet votant + duel)
MSG2VOTE = dict() #associe un message d'inscription au vote à une élection -> pour envoyer un message privé pour voter

async def dmChannelUser(user):
    if user.dm_channel is None:
        await user.create_dm() #crée le dm channel, et après user.dm_channel est remplacé par l'objet représentant le dm channel
    return user.dm_channel

def main():
    from discord.ext import commands, tasks
    
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=prefixeBot, help_command=None, intents = intents) #il faudrait peut-être que je fasse une aide un jour...

    @bot.event #pour ne pas afficher les messages d'erreur de commande inexistante (typiquement si on utilise une commande du bot squadro qui est gérée par un autre script)
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        raise error

    async def ajoutDuel(votant, opt1, opt2, channel): #crée un message permettant de se positionner sur un duel
        msg = await channel.send(":arrow_left: {} ou {} :arrow_right: ?".format(opt1, opt2))
        await msg.add_reaction("⬅️")
        #await msg.add_reaction("↔️")
        await msg.add_reaction("➡️")
        votant.ajouteMessageDuel((opt1, opt2), msg.id)

        MSG2DUEL[msg.id] = (votant, (opt1, opt2))

    @bot.event
    async def on_reaction_add(reaction, user): #pour enregistrer la position du votant sur un duel / commencer à voter / envoyer un nouveau duel
        if user.id == bot.user.id: return

        message = reaction.message
        emoji = reaction.emoji
        userId = user.id
        channel = await dmChannelUser(user)

        if message.id in MSG2VOTE: #on est là après avoir cliqué sur la réaction pour voter
            if userId not in {619574125622722560, 476163854858977309, 495283249493442570, 257924378795180032, 356510267833712645, 646480116884570162, 690496497476960256, 235694387248627712, 519205599548801034}:
                await channel.send("Tu n'as le droit de voter que si t'es dans le groupe 9B…")
                return

            election = MSG2VOTE[message.id]
            if election.fini():
                await channel.send("Désolé, le dépouillement a déjà eu lieu")
                return

            votant = election.getVotant(userId)

            opt1, opt2 = votant.duelAFaire(start = True)
            if len(election.candidats) > 2:
                await channel.send("Pour enregistrer ton vote, j'ai besoin d'un ordre de préférence complet.\nComme c'est un peu relou de le faire soi-même, je vais juste te demander qui tu préfères dans quelques duels de candidat(e)s, et j'en déduirai ton ordre de préférence complet.")
            else:
                await channel.send("Pour enregistrer ton vote, t'as juste à préciser avec :arrow_left: ou :arrow_right: ta préférence.")

            await ajoutDuel(votant, opt1, opt2, channel)

        elif message.id in MSG2DUEL: #on a voté sur un duel
            votant, (opt1, opt2) = MSG2DUEL[message.id]

            if emoji in ("⬅️", "➡️", "↔️") and not votant.duelFait(opt1, opt2):
                if emoji == "↔️":
                    prefere = None
                else:
                    prefere = opt1 if emoji == "⬅️" else opt2
                votant.ajoutPreference(opt1, opt2, prefere)

                if prefere is None: prefere = "Neutre" #pour un affichage plus parlant que None
                await message.edit(content = ":arrow_left: {} ou {} :arrow_right:\n**Vote enregistré : {}**".format(opt1, opt2, prefere))

                nouvDuel = votant.duelAFaire()
                if nouvDuel: #on doit faire un nouveau duel pour avoir le classement complet, on l'envoie
                    opt1, opt2 = nouvDuel

                    await ajoutDuel(votant, opt1, opt2, channel)

                else: #pas besoin d'un nouveau duel, on a fini !
                    classement = votant.calculClassement()
                    affi = "Ton classement :\n"
                    affi += "\n".join(f"**{index+1}** {opt}" for (opt, index) in classement)

                    await channel.send(affi)
                    msgReplay = await channel.send("**Ton vote a été enregistré.**\nPour changer ton vote, réagis à ce message avec 🔂")
                    await msgReplay.add_reaction("🔂") #réaction pour changer le vote
                    MSG2VOTE[msgReplay.id] = votant.election

                    #on change l'affichage du nombre de votants
                    nbVotants = votant.election.nbVotesValides()
                    for msg in votant.election.msgInfo:
                        await msg.edit(content = "**Réagissez à ce message pour participer au vote.**\n {} votes ont été enregistrés pour le moment.".format(nbVotants))

    @bot.command(name="vote_setup") #pour démarrer à paramétrer une élection
    async def startvote(ctx, sysVote = "RankedPairs"):
        if sysVote not in Election.sysVotes:
            await ctx.send("Ce système de vote n'est pas pris en charge…")
            await ctx.send("Liste des systèmes de vote pris en charge : {}".format(", ".join(Election.sysVotes)))
        else:
            from random import randint
            int_to_hex = lambda x: hex(x)[2:]

            election = Election(sysVote)
            idElection = int_to_hex(randint(1000000, 9999999))

            ELECTIONS[idElection] = (election, ctx.author.id)

            await ctx.send("L'élection est enregistrée sous l'identifiant {id}.\nPour la configurer, utilisez les commandes `{cmd}vote_addopt {id} nomOption` pour ajouter une option, `{cmd}vote_remopt {id} nomOption` pour la retirer…\nUne fois configurée, il faut lancer le vote avec la commande `{cmd}vote_start {id}` et `{cmd}vote_end {id}` pour lancer le dépouillement".format(id = idElection, cmd = prefixeBot))

    @bot.command(name="vote_addopt") #pour ajouter une option de vote à une élection (seulement avant le début du vote...)
    async def addopt(ctx, idElection, nomOption):
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            election, auteurId = ELECTIONS[idElection]
            if auteurId != ctx.author.id:
                return

            if election.commence:
                await ctx.send("Le vote a été lancé, il n'est plus possible d'ajouter une option de vote")
            else:
                election.candidats.add(nomOption)
                await ctx.send("L'option \"{}\" a bien été ajoutée".format(nomOption))

    @bot.command(name="vote_remopt") #pour retirer une option de vote à une élection (seulement avant le début du vote...)
    async def remopt(ctx, idElection, nomOption):
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            election, auteurId = ELECTIONS[idElection]
            if auteurId != ctx.author.id:
                return

            election.candidats.remove(nomOption)
            await ctx.send("{} ne fait plus partie des options de cette élection".format(nomOption))

    @bot.command(name="vote_start") #pour démarrer le vote + envoyer le message permettant de participer au vote
    async def start(ctx, idElection):
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            from time import sleep

            election, auteurId = ELECTIONS[idElection]
            if auteurId != ctx.author.id:
                return

            if len(election.candidats) >= 2: #on peut commencer le vote, il y a plusieurs candidats
                election.commence = True

                try:
                    await ctx.message.delete()
                except:
                    pass

                await ctx.send("**C'est parti pour le vote !** Voici les candidatures :\n- {}".format("\n- ".join(sorted(election.candidats))))

                nbVotants = election.nbVotesValides()
                msg = await ctx.send("**Réagissez à ce message pour participer au vote.**\n {} votes ont été enregistrés pour le moment.".format(nbVotants))
                await msg.add_reaction("🗳️")

                MSG2VOTE[msg.id] = election
                election.msgInfo.append(msg)
            else:
                await ctx.send("Il n'y a pas assez d'options dans l'élection, impossible de lancer le vote dans ces conditions… (il en faut au moins 2...)")

    @bot.command(name="vote_end") #pour lancer le dépouillement
    async def endvote(ctx, idElection):
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            election, auteurId = ELECTIONS[idElection]
            if auteurId != ctx.author.id:
                return

            election.calculVote()
            for msg in election.msgInfo:
                txt = msg.content
                await msg.edit(content = txt + "\nLE VOTE EST MAINTENANT CLOS")

            await affires(ctx, idElection)

    @bot.command(name="vote_affires") #pour afficher les résultats une fois le dépouillement fait
    async def affires(ctx, idElection):
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            from time import sleep
            election, auteurId = ELECTIONS[idElection]

            if not election.fini():
                await ctx.send("Le dépouillement n'a pas encore eu lieu…")
                return

            classement = election.getResultats()

            await ctx.send("**Résultats de l'élection :**")
            msgs, fichiers = election.affi()

            for msg in msgs:
                await ctx.send(msg)
                sleep(0.5) #on attend 1/2 seconde entre chaque message, sinon discord est vite en PLS

            if fichiers:
                for fichier in fichiers:
                    await ctx.send(file = discord.File(fichier))
                    sleep(0.5)

    @bot.command(name="vote_addalias") #pour mettre un autre message pour lancer le vote, par exemple dans un autre salon
    async def addalias(ctx, idElection):
        await start(ctx, idElection)

    @bot.command(name="vote_affconfig")
    async def configelec(ctx, idElection): #pour voir la configuration actuelle d'une élection
        if idElection not in ELECTIONS:
            await ctx.send("L'identifiant d'élection n'est pas valide…")
        else:
            election, auteurId = ELECTIONS[idElection]
            if auteurId != ctx.author.id: return

            info = "**Configuration de l'élection**\n"

            info += "Options de vote :" + ", ".join(election.candidats) + "\n"
            info += "Système de vote : {}".format(election.sysVote)

            await ctx.send(info)

    return bot, TOKEN

if __name__ == "__main__": #pour lancer le bot
    bot, token = main()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

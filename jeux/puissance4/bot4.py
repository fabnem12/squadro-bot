import asyncio
import nextcord
import pickle, os
from nextcord.ext import commands

from puissance4 import Game

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from constantes import TOKEN
from utils import stockePID, cheminOutputs as outputsPath
stockePID()

joueur2partie = dict()
parties = dict()
class Partie:
    def __init__(self, joueur1, joueur2):
        self.joueurs = [joueur1, joueur2]
        self.msgs = []
        self.joueurEnCours = 0
        self.partie = Game(joueur1.id, joueur2.id)

    def aQuiDeJouer(self):
        return self.joueurs[self.joueurEnCours]

    def affiPlateau(self):
        return self.partie.drawTab()

    def joue(self, coup):
        if coup not in (1, 2, 3, 4, 5, 6, 7): return False

        ret = self.partie.action(coup)
        if ret:
            self.joueurEnCours = 1-self.joueurEnCours
            return True
        else:
            return False

    def gagnant(self):
        potGagnant = self.partie.four()
        if potGagnant:
            return self.joueurs[potGagnant-1]
        else:
            return None

def main():
    intentsBot = nextcord.Intents.default()
    intentsBot.members = True
    intentsBot.messages = True
    intentsBot.message_content = True
    bot = commands.Bot(command_prefix="T.", help_command=None, intents = intentsBot)

    @bot.slash_command(guild_ids=[712348902073827479, 603692346273693697])
    async def puissance_quatre(interaction: nextcord.Interaction, joueur2: nextcord.Member):
        joueur1 = interaction.user
        partie = Partie(joueur1, joueur2)
        parties[joueur1.id, joueur2.id] = partie
        joueur2partie[joueur1.id] = partie
        joueur2partie[joueur2.id] = partie

        msg = await interaction.response.send_message(f"Partie entre {joueur1.mention} et {joueur2.mention}.\nÀ {joueur1.mention} de jouer", file = nextcord.File(partie.affiPlateau()))

    @bot.command(name = "puissance_quatre")
    async def puissance_quatre2(ctx, joueur2: nextcord.Member):
        joueur1 = ctx.author
        partie = Partie(joueur1, joueur2)
        parties[joueur1.id, joueur2.id] = partie
        joueur2partie[joueur1.id] = partie
        joueur2partie[joueur2.id] = partie

        msg = await ctx.send(f"Partie entre {joueur1.mention} et {joueur2.mention}.\nÀ {joueur1.mention} de jouer", file = nextcord.File(partie.affiPlateau()))
        partie.msgs.append(msg.id)

    @bot.command(name = "coup")
    async def coup(ctx, coup: int):
        joueur = ctx.author
        if joueur.id in joueur2partie:
            partie = joueur2partie[joueur.id]

            if partie.aQuiDeJouer().id == joueur.id:
                coupOk = partie.joue(coup)
                partie.msgs.append(ctx.message.id)

                if partie.gagnant() is None:
                    if coupOk:
                        msg = await ctx.send(f"À {partie.aQuiDeJouer().mention} de jouer !", file = nextcord.File(partie.affiPlateau()))
                    else:
                        msg = await ctx.send("Le coup est invalide ! Essaie encore")
                else:
                    gagnant = partie.gagnant()

                    if gagnant:
                        msg = await ctx.send(f"{gagnant.mention} a cordialement écrasé son adversaire :tada:", file = nextcord.File(partie.affiPlateau()))
                    else: #match nul
                        msg = await ctx.send("Match nul !", file = nextcord.File(partie.affiPlateau()))

            else:
                msg = await ctx.send(f"Ce n'est pas à toi de jouer ! C'est le tour {partie.aQuiDeJouer().mention}")

            partie.msgs.append(msg.id)
        else:
            await ctx.send("Vous n'êtes dans aucune partie")

    @bot.command(name = "efface_partie")
    async def efface_partie(ctx):
        joueur = ctx.author
        if joueur.id in joueur2partie:
            partie = joueur2partie[joueur.id]

            if partie.gagnant():
                for msgId in partie.msgs:
                    msg = await ctx.channel.fetch_message(msgId)
                    await msg.delete()

                joueurs = tuple(partie.joueurs)
                for joueur in joueurs:
                    del joueur2partie[joueur.id]
                del parties[joueurs]

            else:
                await ctx.send("Je ne peux pas faire ça tant que la partie n'est pas terminée")
        else:
            await ctx.send("Impossible de supprimer une partie")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(TOKEN))
    loop.run_forever()

main()

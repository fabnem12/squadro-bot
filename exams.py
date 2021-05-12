import asyncio
import csv
import discord
import os
import sys

from discord.ext import commands
from typing import Optional, Union, Dict, Set, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#CONSTANTES
from constantes import ADMINS, TOKEN, prefixeBot
from utils import stockePID, cheminOutputs

stockePID()

cheminCsv = os.path.join(cheminOutputs, "exams")
fichiers = {"bdd": "BDD.csv", "igsd": "IGSD.csv", "mdd251": "MDD251.csv", "mdd252": "MDD252.csv", "mdd253": "MDD253.csv", "pogl": "POGL.csv"}

def seekInfo(matiere: str, numEtudiant: str) -> str:
    fichierMatiere = os.path.join(cheminCsv, fichiers[matiere])

    res = None
    try:
        with open(fichierMatiere, newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row["N° étudiant"].replace(" ", "") == numEtudiant:
                    res = row
                    break
    except:
        return "Erreur lors de la lecture du fichier"

    if res is None:
        return "Aucune information trouvée…"
    else:
        return f"Infos pour l'examen de {matiere.upper()}\n\n" + "\n".join(f"**{a}** {b}" for a, b in res.items() if b != "")

def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None, intents = discord.Intents.all())

    async def dmChannelUser(user):
        if user.dm_channel is None:
            await user.create_dm() #crée le dm channel, et après user.dm_channel est remplacé par l'objet représentant le dm channel
        return user.dm_channel

    @bot.command(name = "exams")
    async def affiInfosMatiere(ctx, matiere: Optional[str], numEtudiant: Optional[str]):
        ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)
        if matiere: matiere = matiere.lower()

        channel = await dmChannelUser(ctx.author)

        if matiere is None:
            affi = "Pour avoir des informations sur un examen, vous pouvez utiliser les commandes suivantes :\n"
            affi += "\n".join(f"- `{prefixeBot}exams {matiere} numeroEtudiant`" for matiere in fichiers)
            affi += "\n\nLe bot répondra en privé"

            await ctx.send(affi, reference = ref)
        elif matiere not in fichiers:
            await channel.send(f"Matière inconnue : '{matiere}'")
            await affiInfosMatiere(ctx, None, None)
        else:
            if numEtudiant is None:
                await channel.send(f"Il faut donner un numéro d'étudiant : `{prefixeBot}exams {matiere} numEtudiant`")
            else:
                await channel.send(seekInfo(matiere, numEtudiant))

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

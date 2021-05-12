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

def seekInfo(fichierMatiere: str, numEtudiant: str) -> str:
    res = None
    try:
        with open(fichierMatiere, newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if numEtudiant in row["N° étudiant"] or row["N° étudiant"] in numEtudiant:
                    res = row
                    break
    except:
        return "Erreur lors de la lecture du fichier"

    if res is None:
        return "Aucune information trouvée…"
    else:
        return "\n".join(f"**{a}** {b}" for a, b in res.items() if b != "")

def main():
    bot = commands.Bot(command_prefix = prefixeBot, help_command = None, intents = discord.Intents.all())

    @bot.command(name = "exams")
    async def affiInfosMatiere(ctx, matiere: Optional[str], numEtudiant: Optional[str]):
        ref = discord.MessageReference(message_id = ctx.message.id, channel_id = ctx.channel.id)
        matiere = matiere.lower()

        if matiere is None:
            affi = "Pour avoir des informations sur un examen, vous pouvez utiliser les commandes suivantes :\n"
            affi += "\n".join(f"- `{prefixeBot}exams {matiere}` numeroEtudiant" for matiere in fichiers)

            await ctx.send(affi, reference = ref)
        elif matiere not in fichiers:
            await ctx.send(f"Matière inconnue : '{matiere}'", reference = ref)
            await affiInfosMatiere(ctx, None, None)
        else:
            nomFichier = fichiers[matiere]
            if numEtudiant is None:
                await ctx.send(f"Il faut donner un numéro d'étudiant : `{prefixeBot}exams {matiere} numEtudiant`", reference = ref)
            else:
                await ctx.send(seekInfo(os.path.join(cheminCsv, nomFichier), numEtudiant), reference = ref)

    return bot, TOKEN

if __name__ == "__main__":
    bot, token = main()

    bot.run(token)

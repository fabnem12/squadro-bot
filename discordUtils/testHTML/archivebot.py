import asyncio
import discord
import os
import pickle
import re
from discord.ext import commands
from datetime import datetime, timedelta
from random import randint
from typing import Callable, Dict, Optional, Tuple

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constantes import TOKEN #le token du bot pour se connecter à discord
from utils import cheminOutputs, stockePID

stockePID()

sautDeLigne = "\n"

def msg2html(msg, previousAuthor = None):
    import demoji
    import requests

    #print(msg)
    #input()

    #on gère le formattage simple (gras, souligné, italique)
    from markdown import markdown
    txt = markdown(msg.content).replace("<p>", "").replace("</p>", "").replace("\n", "<br/>")

    #---- on extrait les emojis non standard -> texte du message
    emojis = re.findall(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>", msg.content)
    #emojis2 = list(map(lambda x: (x, hex(ord(x))[2:]), demoji.findall(txt).keys()))
    emojis2 = list(map(lambda info: (info[0], "-".join(map(lambda y: hex(ord(y))[2:], info[0])), info[1]), demoji.findall(txt).items()))

    #on regarde si le message ne contient que des emojis / espaces
    testQueEmoji = txt.replace(" ", "")
    for emoji in emojis:
        anime, nom, ident = emoji
        testQueEmoji = testQueEmoji.replace(f"<{anime}:{nom}:{ident}>", "")
    for raw, emojiIdent, desc in emojis2:
        testQueEmoji = testQueEmoji.replace(raw, "")

    queEmoji = testQueEmoji == ""

    #on remplace les emojis par les images
    #mais d'abord on fait les combinaisons d'emoji possibles

    def convertEmoji(anime, nom, ident):
        urlEmoji = f"https://cdn.discordapp.com/emojis/{ident}.{'gif' if anime == 'a' else 'png'}"
        return f"<img src='{urlEmoji}' class=\'{'emoji_grand' if queEmoji else 'emoji_petit'}\' title='{nom}' />"
    def convertEmoji2(raw, emojiIdent, desc):
        if "keycap" not in desc or "10" in desc:
            urlEmoji = f"https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/{emojiIdent}.svg"
        else:
            nomChiffre = {"1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine"}[desc[-1]]
            urlEmoji = f"https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/160/twitter/282/keycap-digit-{nomChiffre}_{emojiIdent}.png"

        return f"<img src='{urlEmoji}' class=\'{'emoji_grand' if queEmoji else 'emoji_petit'}\' title='{desc}' />"

    for anime, nom, ident in emojis:
        txt = txt.replace(f"<{anime}:{nom}:{ident}>", convertEmoji(anime, nom, ident))
    for raw, emojiIdent, desc in emojis2:
        txt = txt.replace(raw, convertEmoji2(raw, emojiIdent, desc))

    #---- affichage des détails d'envoi (auteur + date / heure)
    detailsAuteur, heureCachee = "", ""
    #on ne met rien sur l'auteur si le précédent est le même

    moment = msg.created_at
    author = msg.author
    jourSemaine = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"][moment.weekday()]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"][moment.month-1]
    infoMomentVerbose = f"{jourSemaine} {moment.day} {mois} {moment.year} {str(moment.hour).zfill(2)}:{str(moment.minute).zfill(2)}"

    if author != previousAuthor:
        detailsAuteur = f"\n            <tr>\n"
        detailsAuteur += f"              <td rowspan='2' class='conteneur_avatar'>\n"
        detailsAuteur += f"                <img src='{author.avatar_url}' class='avatar' />\n              </td>\n              <td>\n                <span class='author'>{author.name if isinstance(author, discord.User) else author.nick or author.name}</span>\n"
        detailsAuteur += f"                <span class='date' title='{infoMomentVerbose}'>{str(moment.day).zfill(2)}/{str(moment.month).zfill(2)}/{moment.year}</span>\n"
        detailsAuteur += f"              </td>\n            </tr>"
    else:
        heureCachee = f"\n              <td class='heure_cachee' title='{infoMomentVerbose}'>\n                {str(moment.hour).zfill(2)}:{str(moment.minute).zfill(2)}\n              </td>"

    #---- code html total
    htmlTotal = f"""        <article>
            <table>{detailsAuteur}
              <tr>{heureCachee}
                <td class="txt_message">
                  {txt}
                </td>
              </tr>
            </table>
        </article>
"""

    return htmlTotal

async def ecritHtml(channel):
    listeHtml = []
    print(0)

    previousAuthor = None
    i = 1
    async for msg in channel.history(limit = None, oldest_first = True):
        listeHtml.append(msg2html(msg, previousAuthor))
        previousAuthor = msg.author

        print(i)
        i += 1

    with open("output.htm", "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
  <head>
    <title>
      Magnifique test
    </title>
    <link rel="stylesheet" href="discord.css" />
    <style> /* Couleurs des rôles */
      .role804759289000493056 {{
        color: #efc30f;
      }}
      .role811672982593339422 {{
        color: #744d88;
      }}
    </style>
  </head>
  <body>
    <header>
      <div class="conteneur_gauche">
        <div class="nom_serveur">
        {channel.guild.name}
        </div>
      </div>
      <div class="nom_salon">
        # {channel.name}
      </div>
    </header>
    <div id="conteneur_global">
      <div class="conteneur_gauche">
        <nav>
          <ul>
            {sautDeLigne.join("<li># {}</li>".format(channelAutre.name) for channelAutre in channel.guild.text_channels)}
          </ul>
        </nav>
      </div>
      <section>""")
        f.write("".join(listeHtml))
        f.write("""      </section>
    </div>
  </body>
</html>
""")

    return "output.htm"

def main():
    bot = commands.Bot(command_prefix="A,", help_command = None)

    @bot.event
    async def on_message(msg):
        await bot.process_commands(msg)

    @bot.command(name="archive")
    async def archive(ctx):
        filePath = await ecritHtml(ctx.channel)
        await ctx.send(file = discord.File(filePath))

    @bot.command(name = "test")
    async def test(ctx):
        print(ctx.message.content, "\U0001F44D" in ctx.message.content)

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(TOKEN))
    loop.run_forever()

main()

import asyncio
import discord
import os
from datetime import datetime, timedelta
from discord.ext import commands
from typing import Dict, List, Tuple, Union, Optional, Set

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix
from utils import stockePID, cheminOutputs as outputsPath

#token = "" #bot token
#prefix = ","
bumpBot = 302050872383242240 #DISBOARD
botCommandsChannel = 577955068268249098 #bot-commands

async def countMessages(guild):
    now = datetime.now()
    currentMonth = now.month
    previousMonth = (currentMonth - 1) if currentMonth != 1 else 12
    yearOfPrevMonth = now.year if currentMonth != 1 else now.year -1

    def numberOfDays(month):
        if month in {1, 3, 5, 7, 8, 10, 12}:
            return 31
        elif month == 2:
            if yearOfPrevMonth % 4 == 0 and (yearOfPrevMonth % 400 == 0 or yearOfPrevMonth % 100 != 0):
                return 29
            else:
                return 28
        else:
            return 30

    #let's find the beginning and the end of the previous month according to UTC
    timeLimitEarly = datetime(yearOfPrevMonth, previousMonth, 1) - timedelta(hours = 2)
    timeLimitLate = datetime(yearOfPrevMonth, previousMonth, numberOfDays(previousMonth)) - timedelta(hours = 2)

    #the file will be stored here… the bot will send the txt file when the counting is done
    pathSave = os.path.join(outputsPath, "infoTopCountries.txt")
    with open(pathSave, "w") as f: f.write("Work in progress…")

    nbMsgPerCountry = dict()
    nbMsgPerMultinational = dict()
    keyDicoByAuthorId = dict()

    countries = {"United Kingdom", "Ireland", "Portugal", "Spain", "France", "Belgium", "Netherlands", "Luxembourg", "Germany", "Italy", "Switzerland", "Malta", "Norway", "Sweden", "Denmark", "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus", "Czechia", "Slovakia", "Austria", "Slovenia", "Croatia", "Greece", "Bulgaria", "Romania", "Ukraine", "Turkey", "Cyprus", "Russia", "Armenia", "Azerbaijan", "Israel", "Georgia", "Lebanon", "North America", "South America", "Africa", "Asia", "Oceania", "Kazakhstan"}
    for channel in guild.text_channels: #let's read all the channels
        try: #discord raises Forbidden errors if the bot is not allowed to read messages in "channel"
            with open(pathSave, "w") as f: f.write(f"Counting in <#{channel.id}>")
            #print(channel.name)

            #i = 0
            async for msg in channel.history(limit = None, after = timeLimitEarly, before = timeLimitLate): #let's read the messages sent last month in the current channel
                #i += 1
                #if i % 100 == 0: print(i)

                author = msg.author
                try:
                    if author.id not in keyDicoByAuthorId:
                        author = await guild.fetch_member(author.id)
                except: #the author left the server, there is no way to know their country roles…
                    continue

                if author.id not in keyDicoByAuthorId:
                    authorsCountries = tuple(role.name for role in author.roles if role.name in countries)
                    if len(authorsCountries) == 1: #the author has only 1 country role: easy
                        key = authorsCountries[0]
                        dico = nbMsgPerCountry
                    else: #the author has several country roles, it's up to Isak!
                        key = author.nick or author.name
                        dico = nbMsgPerMultinational

                    keyDicoByAuthorId[author.id] = (key, dico)
                else:
                    key, dico = keyDicoByAuthorId[author.id]

                if key not in dico: #increase the count of messages
                    dico[key] = 1
                else:
                    dico[key] += 1

            #if input() != "": break
        except: pass

    with open(pathSave, "w") as f:
        f.write("Top countries (with mono-nationals only):\n\n")
        f.write("\n".join(f"{country} {nbMsgs}" for country, nbMsgs in sorted(nbMsgPerCountry.items(), key=lambda x: x[1], reverse = True)))
        f.write("\n\nTop multi-national users:\n")
        f.write("\n".join(f"{name} {nbMsgs}" for name, nbMsgs in sorted(nbMsgPerMultinational.items(), key=lambda x: x[1], reverse = True)))

    quit()

def main() -> None:
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    @bot.event
    async def on_ready():
        print("toto")
        await countMessages(bot.get_guild(567021913210355745))

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

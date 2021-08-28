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

def eurovisionPoints(topPerChannel, keyDicoByAuthorId):
    print(len(topPerChannel), len(keyDicoByAuthorId))
    points = dict()
    affi = ""

    def addPoints(key, nbPoints):
        if key not in points:
            points[key] = nbPoints
        else:
            points[key] += nbPoints

    for channel, (top, channelName) in topPerChannel.items():
        rankedTop = sorted(top.items(), key=lambda x: x[1], reverse = True)

        if len(rankedTop) >= 10 and rankedTop[9][1] >= 150: #if not, let's just ignore this channel for the eurovision points, it's not relevant
            #recap of the channel
            affiChannel = f"Top in #{channelName}\n"
            affiChannel += "\n".join(f"#{i+1} {keyDicoByAuthorId[authorId][2]}" for i, (authorId, _) in zip(range(10), rankedTop))
            affiChannel += "\n\n"

            affi += affiChannel

            #let's add eurovision points
            for nbPoints, (authorId, _) in zip((12, 10, 8, 7, 6, 5, 4, 3, 2, 1), rankedTop):
                addPoints(authorId, nbPoints)

    topPoints = f"Top users eurovision style:\n"
    topPoints += "\n".join(f"#{i+1} {keyDicoByAuthorId[authorId][2]} with {nbPoints} points" for i, (authorId, nbPoints) in enumerate(sorted(points.items(), key=lambda x: x[1], reverse=True)))

    return topPoints + "\n\n" + affi

async def countMessages(guild, bot):
    now = datetime.now()
    currentMonth = now.month
    previousMonth = (currentMonth - 1) if currentMonth != 1 else 12
    yearOfPrevMonth = now.year if currentMonth != 1 else now.year -1

    #let's find the beginning and the end of the previous month according to UTC
    timeLimitEarly = datetime(yearOfPrevMonth, previousMonth, 1) - timedelta(hours = 2)
    timeLimitLate = datetime(yearOfPrevMonth, currentMonth, 1) - timedelta(hours = 2)

    #the file will be stored here… the bot will send the txt file when the counting is done
    pathSave = os.path.join(outputsPath, "infoTopCountries.txt")

    nbMsgPerCountry = dict()
    nbMsgPerMultinational = dict()
    nbMsgPerPerson = dict()
    topPerChannel = dict()
    keyDicoByAuthorId = dict()

    totalNbMsgs = 0
    countries = {"United Kingdom", "Ireland", "Portugal", "Spain", "France", "Belgium", "Netherlands", "Luxembourg", "Germany", "Italy", "Switzerland", "Malta", "Norway", "Sweden", "Denmark", "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus", "Czechia", "Slovakia", "Austria", "Slovenia", "Croatia", "Greece", "Bulgaria", "Romania", "Ukraine", "Turkey", "Cyprus", "Russia", "Armenia", "Azerbaijan", "Israel", "Georgia", "Lebanon", "North America", "South America", "Africa", "Asia", "Oceania", "Kazakhstan", "San Marino"}
    for channel in filter((lambda x: "logs" not in x.name), guild.text_channels): #let's read all the channels
        try: #discord raises Forbidden error if the bot is not allowed to read messages in "channel"
            await bot.change_presence(activity=discord.Game(name=f"Counting messages in #{channel.name} - {totalNbMsgs}+ messages counted so far"))

            topChannel = dict()
            topPerChannel[channel.id] = (topChannel, channel.name)

            async for msg in channel.history(limit = None, after = timeLimitEarly, before = timeLimitLate): #let's read the messages sent last month in the current channel
                totalNbMsgs += 1

                if totalNbMsgs % 2000 == 0:
                    await bot.change_presence(activity=discord.Game(name=f"Counting messages in #{channel.name} - {totalNbMsgs}+ messages counted so far"))

                author = msg.author
                try:
                    if author.id not in keyDicoByAuthorId:
                        author = await guild.fetch_member(author.id)

                        if author.bot: continue
                except: #the author left the server, there is no way to know their country roles…
                    continue

                msgLength = len(msg.content)

                if author.id not in keyDicoByAuthorId:
                    authorsCountries = tuple(role.name for role in author.roles if role.name in countries)
                    if len(authorsCountries) == 1: #the author has only 1 country role: easy
                        key = authorsCountries[0]
                        dico = nbMsgPerCountry
                    else: #the author has several country roles, it's up to Isak!
                        key = f"{author.nick} ({author.name})" if author.nick else author.name
                        dico = nbMsgPerMultinational

                    keyDicoByAuthorId[author.id] = (key, dico, f"{author.nick} ({author.name})" if author.nick else author.name)
                else:
                    key, dico, authorNick = keyDicoByAuthorId[author.id]

                if key not in dico: #increase the count of messages
                    dico[key] = msgLength
                else:
                    dico[key] += msgLength

                if author.id not in nbMsgPerPerson:
                    nbMsgPerPerson[author.id] = msgLength
                else:
                    nbMsgPerPerson[author.id] += msgLength

                if author.id not in topChannel:
                    topChannel[author.id] = msgLength
                else:
                    topChannel[author.id] += msgLength

        except Exception as e:
            print(e)

    with open(pathSave, "w") as f:
        f.write("Top countries (with mono-nationals only):\n\n")
        f.write("\n".join(f"{country} with {nbMsgs} letters" for country, nbMsgs in sorted(nbMsgPerCountry.items(), key=lambda x: x[1], reverse = True)))
        f.write("\n\nTop multi-national users:\n")
        f.write("\n".join(f"{name} with {nbMsgs}x20 letters" for name, nbMsgs in sorted(nbMsgPerMultinational.items(), key=lambda x: x[1], reverse = True)))
        f.write("\n\nTop 100 users of the month:\n")
        f.write("\n".join(f"#{i+1} {keyDicoByAuthorId[authId][2]} with {nbMsgs} letters" for i, (authId, nbMsgs) in zip(range(100), sorted(nbMsgPerPerson.items(), key=lambda x: x[1], reverse = True))))
        f.write("\n\n")
        f.write(eurovisionPoints(topPerChannel, keyDicoByAuthorId))

    await bot.change_presence()
    quit()

def main() -> None:
    bot = commands.Bot(command_prefix=prefix, help_command=None)

    @bot.event
    async def on_ready():
        await countMessages(bot.get_guild(567021913210355745), bot)

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()

main()

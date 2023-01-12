import asyncio
import nextcord
from nextcord.ext import commands, tasks
import numpy as np
import os
import pickle
import youtube_dl
from arrow import utcnow

from constantes import tokenUrsula as TOKEN, APItwi, APItwiSec
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

def main() -> None:
    intentsBot = nextcord.Intents.default()
    intentsBot.members = True
    intentsBot.messages = True
    intentsBot.message_content = True
    bot = commands.Bot(command_prefix="S.", help_command=None, intents = intentsBot)
    
    @tasks.loop(minutes = 1.0)
    async def autoplanner():
        now = utcnow().to("Europe/Brussels")
        if now.hour in (0, 6, 12, 18) and now.minute == 0:
            await sendUrsula(None)

    @bot.command(name = "kill_ursula")
    async def killBot(ctx):
        if ctx.author.id == 619574125622722560:
            quit()

    @bot.command("ursula")
    async def sendUrsula(ctx):
        if ctx is None:
            guild = bot.get_guild(712348902073827479)
            channel = await guild.fetch_channel(765232858499252264)
        else:
            channel = ctx.channel
        


    bot.run(TOKEN)

if __name__ == "__main__":
    main()

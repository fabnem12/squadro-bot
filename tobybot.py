import discord
from discord.ext.commands import Bot
from discord.ext import commands
import asyncio
import random
import pickle
import os

Client = discord.Client()
client = commands.Bot(command_prefix = "TobyBot ,")

@client.event
async def on_ready():
    print("Bot is ready!")
    await (await client.fetch_channel("618098494816780338")).send("Salut, je viens de me réveiller (ou alors j'ai eu une mise à jour)")

@client.event
async def on_message(message):
    msg = message.content.upper()
    if msg.startswith("TEST"):
        await message.channel.send("ça marche bg")
    elif msg.startswith("PATRICK"):
        await message.channel.send("MASSOT")
    elif msg.endswith("OUI"):
        await message.channel.send("STITI")
    elif msg.endswith("QUOI"):
        await message.channel.send("FEUR")

    elif msg.startswith("TOBYBOT, "):
        if msg.startswith("TOBYBOT, DIS"):
        #    if message.author.id != "686694119648919553":
            args = message.content.split(" ")
            await message.delete()
            await message.channel.send(" ".join(args[2:]))
    

client.run('Njg2Njk0MTE5NjQ4OTE5NTUz.XmzIdA.u1aXTRDxguDR2YfaUYXpZLKyytI')

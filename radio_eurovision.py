import asyncio
import nextcord
from nextcord.ext import commands
import numpy as np
import os
import pickle
import youtube_dl
from arrow import get as arrowGet, utcnow

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

if os.path.exists("radioEurovision.p"):
    videos = pickle.load(open("radioEurovision.p", "rb"))
else:
    videos = dict()

def planning():
    #aléa en fonction de la date
    moment = utcnow().to("Europe/Brussels")
    seconde = moment.hour*3600 + moment.minute*60 + moment.second
    np.random.seed((moment.year, moment.month, moment.day))

    infosVideos = list(videos.items())

    #on génère le planning du jour, en s'arrêtant quand on arrive à l'heure actuelle
    track = [np.random.randint(len(infosVideos))]
    dureeCumulee = infosVideos[track[-1]][1]

    while dureeCumulee < seconde:
        numTrack = np.random.randint(len(infosVideos))
        while numTrack == track[-1]: #on ne veut pas avoir deux fois la même chanson d'affilée
            numTrack = np.random.randint(len(infosVideos))
        
        #on ajoute la nouvelle chanson à la pile
        track[-1] = numTrack
        dureeCumulee += infosVideos[numTrack][1]
    
    #on a maintenant la chanson en cours
    numTrack = track[-1]
    #mais il est probable que l'on soit à un stade avancé de la vidéo : il faut voir à quel moment de la vidéo on est
    timeLeft = dureeCumulee - seconde
    startTime = infosVideos[numTrack][1] - timeLeft

    return infosVideos[numTrack][0], f"{startTime//60}:{str(startTime%60).zfill(2)}"


youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {'format': 'bestaudio/best', 'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
    'ignoreerrors': True, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto',
    'source_address': '0.0.0.0', 'outtmpl': "outputs" + '/%(title)s.%(ext)s' # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename, data["duration"]


def main() -> None:
    intentsBot = nextcord.Intents.default()
    intentsBot.members = True
    intentsBot.messages = True
    intentsBot.message_content = True
    bot = commands.Bot(command_prefix="S.", help_command=None, intents = intentsBot)

    @bot.command(name = "add_track")
    async def addTrack(ctx, url):
        if ctx.author.id != 619574125622722560: return

        try:
            filename, duration = await YTDLSource.from_url(url, loop=bot.loop)
        except Exception as e:
            await ctx.send(f"Erreur: {e}")
        else:
            videos[filename] = duration

            pickle.dump(videos, open("radioEurovision.p", "wb"))
            await ctx.message.add_reaction("👌")

    @bot.slash_command(name='eurovision', description='Start the Eurovision radio')
    async def join(interaction):
        if not interaction.user.voice:
            await interaction.send("You are not connected to a voice channel! Join one", ephemeral=True)
            return
        else:
            channel = interaction.user.voice.channel
        
        await channel.connect()
        await interaction.send("The bot is playing!", ephemeral=True)
        await play(interaction)

    async def play(interaction):
        server = interaction.guild
        voice_channel = server.voice_client
        if voice_channel is None: return

        url, time = planning()

        async with interaction.channel.typing():
            voice_channel.play(nextcord.FFmpegPCMAudio(source=url, before_options = f"-ss {time}"))
        
        while voice_channel.is_playing():
            await asyncio.sleep(1)

        await play(interaction)

    @bot.slash_command(name='leave', description='Disconnect the Eurovision radio')
    async def leave(interaction):
        voice_client = interaction.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.send("Disconnected", ephemeral=True)
        else:
            await interaction.message.send("The bot is not connected to a voice channel.", ephemeral=True)

    bot.run(token)

if __name__ == "__main__":
    main()

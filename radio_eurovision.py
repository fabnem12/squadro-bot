import asyncio
import nextcord
from nextcord.ext import commands
import numpy as np
import os
import pickle
import youtube_dl
from arrow import utcnow

from constantes import TOKEN as token
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

if os.path.exists("radioEurovision.p"):
    videos = pickle.load(open("radioEurovision.p", "rb"))
else:
    videos = dict()

def planning(seconde = None):
    #aléa en fonction de la date
    moment = utcnow().to("Europe/Brussels")
    if seconde is None:
        seconde = moment.hour*3600 + moment.minute*60 + moment.second
    np.random.seed((moment.year, moment.month, moment.day))

    infosVideos = list(videos.items())

    #on génère le planning du jour, en s'arrêtant quand on arrive à l'heure actuelle
    track = [np.random.randint(len(infosVideos))]
    dureeCumulee = infosVideos[track[-1]][1][0]

    while dureeCumulee < seconde:
        numTrack = np.random.randint(len(infosVideos))
        while numTrack == track[-1]: #on ne veut pas avoir deux fois la même chanson d'affilée
            numTrack = np.random.randint(len(infosVideos))
        
        #on ajoute la nouvelle chanson à la pile
        track[-1] = numTrack
        dureeCumulee += infosVideos[numTrack][1][0]
    
    #on a maintenant la chanson en cours
    numTrack = track[-1]
    #mais il est probable que l'on soit à un stade avancé de la vidéo : il faut voir à quel moment de la vidéo on est
    timeLeft = dureeCumulee - seconde
    startTime = infosVideos[numTrack][1][0] - timeLeft

    return infosVideos[numTrack][0], f"{startTime//60}:{str(startTime%60).zfill(2)}"


youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {'format': 'm4a', 'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
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
    async def addTrack(ctx, url: str, pays: str, annee: int):
        if ctx.author.id != 619574125622722560: return

        try:
            async with ctx.channel.typing():
                filename, duration = await YTDLSource.from_url(url, loop=bot.loop)
        except Exception as e:
            await ctx.send(f"Erreur: {e}")
        else:
            videos[filename] = (duration, pays, annee, url)

            pickle.dump(videos, open("radioEurovision.p", "wb"))
            await ctx.message.add_reaction("👌")

    @bot.command(name="euro")
    async def joinNorm(ctx):
        if not ctx.author.voice:
            await ctx.send("Il faut être connecté dans un salon vocal pour ça !")
            return
        else:
            channel = ctx.author.voice.channel
        
        await channel.connect()
        await play(ctx)

    @bot.slash_command(name='eurovision', description='Démarrer la radio Eurovision')
    async def join(interaction):
        if not interaction.user.voice:
            await interaction.send("Il faut être connecté dans un salon vocal pour ça !", ephemeral=True)
            return
        else:
            channel = interaction.user.voice.channel
        
        await channel.connect()
        await interaction.send("C'est parti !", ephemeral=True)
        await play(interaction)

    async def play(interaction):
        server = interaction.guild
        voice_channel = server.voice_client
        if voice_channel is None: return

        fichier, time = planning()

        async with interaction.channel.typing():
            voice_channel.play(nextcord.FFmpegPCMAudio(source=fichier, before_options = f"-ss {time}"))
        
        while voice_channel.is_playing():
            await asyncio.sleep(1)

        await play(interaction)

    @bot.command(name="fin_euro")
    async def leaveNorm(ctx):
        voice_client = ctx.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()

    @bot.slash_command(name='stop_eurovision', description='Déconnecter la radio Eurovision')
    async def leave(interaction):
        voice_client = interaction.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.send("Déconnecté", ephemeral=True)

    @bot.slash_command(name = "report_track", description = "Signaler qu'un fichier ne marche pas")
    async def signaler(interaction, vraieInteraction = True):
        fichier, _ = planning()

        del videos[fichier]
        os.remove(fichier)
        pickle.dump(videos, open("radioEurovision.p", "wb"))
        if vraieInteraction:
            await interaction.send("Signalé !", ephemeral = True)

        await play(interaction)

        #on le signale à moi
        async def dmChannelUser(user):
            if user.dm_channel is None:
                await user.create_dm()
            return user.dm_channel
        
        moi = await bot.fetch_user(619574125622722560)
        await dmChannelUser(moi).send("Signalement " + fichier)
    
    @bot.command(name = "signaler")
    async def signalerComm(ctx):
        await signaler(ctx, False)
        await ctx.message.add_reaction("👌")
    
    @bot.command(name = "kill_bot")
    async def killBot(ctx):
        if ctx.author.id == 619574125622722560:
            quit()

    @bot.command(name = "affi_planning")
    async def affiPlanning(ctx):
        plan = []

        moment = utcnow().to("Europe/Brussels")
        seconde = 3600*moment.hour + 60*moment.minute + moment.second

        fichier, startTime = planning(seconde)
        debutPremier = sum(x*i + 60*x*(1-i) for i, x in enumerate(map(int, startTime.split(":"))))
        plan.append((fichier, 0))

        secondeNext = seconde - debutPremier
        for _ in range(10):
            secondeNext += videos[fichier][0] + 1

            fichier, _ = planning(secondeNext)
            plan.append((fichier, secondeNext - seconde))
        
        await ctx.send("\n".join(f"__**Maintenant :** {videos[fichier][1:-1]}__" if temps == 0 else f"**Dans {temps//60}:{str(temps%60).zfill(2)} :** {videos[fichier][1:-1]}" for fichier, temps in plan))

    @bot.slash_command(name = "now", description = "Chanson en cours")
    async def now(interaction):
        fichier, avancement = planning()
        _, pays, annee, url = videos[fichier]

        e = nextcord.Embed(title = f"En train de jouer : {pays} {annee}")
        e.set_author(name = "Squadro.py", icon_url = bot.user.avatar.url)
        e.add_field(name = "Lien", value=url, inline=False)

        await interaction.send(embed = e)

    bot.run(token)

if __name__ == "__main__":
    main()

import discord
from discord.ext import commands
import youtube_dl
import asyncio

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, effect):
        options = '-vn' if effect is None else effect+' -vn'

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': options
        }

        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"]
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ytdl_play(self, ctx: commands.Context, url, effect=None):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, effect=effect)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send(f"Now playing: {player.title}")

    @commands.command(name="join")
    async def _join(self, ctx: commands.Context):
        voice = ctx.author.voice.channel
        await voice.connect()

    @commands.command(name="stop", aliases=["leave"])
    async def _stop(self, ctx: commands.Context):
        await ctx.voice_client.disconnect()

    @commands.group(name="play", invoke_without_command=True)
    async def _play(self, ctx: commands.Context, *, url):
        await self.ytdl_play(ctx, url)

    @_play.command(name="bassboost", aliases=["bboost", "boostb", "bb"])
    async def _bboost(self, ctx: commands.Context, *, url):
        await self.ytdl_play(ctx, url, '-af "bass=gain=20"')

    @_play.command(name="pitched", aliases=["p", "pitch"])
    async def _pitch(self, ctx: commands.Context, *, url):
        await self.ytdl_play(ctx, url, '-af "asetrate=r=88K"')

    @_play.command(name="chorus", aliases=["ch"])
    async def _chorus(self, ctx: commands.Context, *, url):
        await self.ytdl_play(ctx, url, '-af "chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3"')


client = commands.Bot('>', description='Ya ebal menya sosali.')
client.add_cog(Music(client))


@commands.has_permissions(administrator=True)
@client.command(name="kill", hidden=True)
async def _kill(ctx):
    await client.close()
    print(f"Bot closed by {ctx.message.author.name}")


@client.event
async def on_ready():
    print(f"Logged in as: {client.user.name} \n-----------------------")

client.run('NjgwNDU2NDU0ODI5ODk5ODAy.XtUriw.rrQJyageTSkZj1EHWk432B5Ex1c')

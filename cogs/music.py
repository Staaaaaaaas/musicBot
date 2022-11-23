import asyncio
import logging
import discord
from discord.ext import commands
import youtube_dl as ytdl
import copy

ytdl.utils.bug_reports_message = lambda: ""

async def set_activity(client: commands.Bot):
    activity = discord.Activity(name='-УШИ', type=discord.ActivityType.listening)
    await client.change_presence(activity=activity)


YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'extract_flat': 'in_playlist',
    'source_address': '0.0.0.0',
}

ydl = ytdl.YoutubeDL(YTDL_OPTIONS)

guild_state = {
    "playlist": [],
    "now_playing": None,
    "prev_message": None,
    "loop": True
}
def parse_effect(effect: str):
    if effect == '-af "bass=gain=20"':
        effect = "(BASSBOOSTED)"
    if effect == '-af "asetrate=r=88K"':
        effect = "(PITCHED)"
    if effect == '-af "chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3"':
        effect = "(CHORUS)"
    return effect

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *,
                 data: dict, volume: float = 1.0, effect: str):

        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data
        self.effect = effect
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.url = data.get('webpage_url')
        self.stream_url = data.get('url')

    def get_embed(self):
        line = "=" * 49
        embed = (discord.Embed(title="Now playing",
                               description=f"**```md\n{self.title} {self.effect}\n{line}\n```**",
                               color=self.requester.color)
                 .add_field(name="Requested by", value=self.requester.mention)
                 .add_field(name="Uploader", value=f"[{self.uploader}]({self.uploader_url})")
                 .add_field(name="URL", value=f"[url]({self.url})")
                 .set_image(url=self.thumbnail))
        return embed

    @classmethod
    async def from_url(cls, ctx: commands.Context, url: str, *,
                       loop: asyncio.BaseEventLoop = None, effect: str):


        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f"{effect} -vn"
        }

        async def _get_info(loop: asyncio.BaseEventLoop, url: str):
            loop = loop or asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            if "_type" in info and info["_type"] == "playlist":
                return await _get_info(loop, info["entries"][0]["url"])

            return info

        data = await _get_info(loop, url)

        effect = parse_effect(effect) 
        filename = data["url"]
        return cls(ctx, discord.FFmpegPCMAudio(filename, **ffmpeg_options), 
                   data=data, effect=effect)

    def __str__(self):
        return self.title


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states = {}

    def get_state(self, guild: discord.Guild):
        if guild.id not in self.states:
            self.states[guild.id] = guild_state
        return self.states[guild.id]

    @commands.Cog.listener()
    async def on_ready(self):
        await set_activity(self.bot)

    async def _play_song(self, ctx: commands.Context, client: discord.VoiceClient,
                         state: dict, song: YTDLSource):
        state["now_playing"] = song
        if state["prev_message"]:
            await state["prev_message"].delete()
        state["prev_message"] = await ctx.send("", embed=state["now_playing"].get_embed())
        def after(_):
            if len(state["playlist"]) > 0:
                next_song = state["playlist"].pop(0)
                if state["loop"]:
                    state["playlist"].append(copy.deepcopy(next_song))
                    print(state["playlist"])
                asyncio.run_coroutine_threadsafe(self._play_song(ctx, client, state, next_song),
                                                 self.bot.loop)
            else:
                asyncio.run_coroutine_threadsafe(client.disconnect(),
                                                 self.bot.loop)
        client.play(song, after=after)

    async def ytdl_play(self, ctx: commands.Context, url: str, effect: str = ""):
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild)
        await ctx.message.add_reaction("👌")
        if client.is_playing():
            try:
                video = await YTDLSource.from_url(ctx, url, effect=effect)
            except ytdl.DownloadError as e:
                logging.warning("Error downloading video: %s", e)
                await ctx.send(
                    "There was an error downloading your video, sorry.")
                return
            state["playlist"].append(video)
            await ctx.send(
                f"Added {video.title} {video.effect} to queue.")
        else:
            try:
                video = await YTDLSource.from_url(ctx, url, effect=effect)
                await self._play_song(ctx, client, state, video)
            except ytdl.DownloadError as e:
                await ctx.send(
                    "There was an error downloading your video, sorry.")
                return


            logging.info("Now playing %s", video.title)

    @commands.guild_only()
    @commands.command(name="join", aliases=["j"])
    async def _join(self, ctx):
        if ctx.author.voice is None:
            raise commands.CommandError("Author not connected to a voice channel")
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

    @commands.guild_only()
    @commands.command(name="loop", aliases=["l", "rep", "repeat"])
    async def _loop(self, ctx):
        state = self.get_state(ctx.guild)
        state["loop"] = not state["loop"]


    @commands.guild_only()
    @commands.command(name="leave", aliases=["lv"])
    async def _stop(self, ctx: commands.Context):
        await ctx.voice_client.disconnect()

    @commands.guild_only()
    @commands.command(name="pause", aliases=["ps"])
    async def _pause(self, ctx: commands.Context):
        voice = ctx.voice_client
        if voice and voice.is_playing():
            voice.pause()

    @commands.guild_only()
    @commands.command(name="resume", aliases=["r"])
    async def _resume(self, ctx: commands.Context):
        voice = ctx.voice_client
        if voice and voice.is_paused():
            voice.resume()

    @commands.guild_only()
    @commands.command(name="skip", aliases=["s"])
    async def _skip(self, ctx: commands.Context):
        await ctx.message.add_reaction("👌")
        ctx.voice_client.stop()

    @commands.guild_only()
    @commands.group(name="play", invoke_without_command=True, aliases=["p"])
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

    @_play.before_invoke
    @_bboost.before_invoke
    @_pitch.before_invoke
    @_chorus.before_invoke
    async def in_voice_channel(self, ctx: commands.Context):
        if ctx.author.voice is None:
            raise commands.CommandError("Author not connected to a voice channel")
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.voice_client.move_to(ctx.author.voice.channel)



def setup(bot):
    bot.add_cog(Music(bot))

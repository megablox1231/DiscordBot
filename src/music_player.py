import os
import asyncio
import yt_download as ydl

import discord
from discord.ext import commands
from discord.ext.commands import Context


FFMPEG_OPTIONS = {
    "executable": os.getenv('FFMPEG'),
    "before_options": '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    "options": '-vn '
}

class MusicPlayer(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue = []

    @commands.command()
    async def test(self, ctx: Context) -> None:
        await ctx.send('Testing')

    @commands.command(help='Tells the bot to join the voice channel')
    async def join(self, ctx: Context):
        if not ctx.message.author.voice:
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()

    @commands.command(help='To make the bot leave the voice channel')
    async def leave(self, ctx: Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect(force=False)
            self.queue = []
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command()
    async def play(self, ctx: Context, *, url: str = None):
        if url is None:
            await ctx.send("Please enter in a YouTube url.")
            return

        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            await ctx.message.author.voice.channel.connect()
            voice_client = ctx.message.guild.voice_client

        if voice_client.is_playing() or self.queue:
            self.queue.append(url)
            await ctx.send("Added to the queue!")
            return

        self.queue.append(url)
        await self.play_next(ctx)

    async def play_next(self, ctx: Context, error=None):
        if self.queue:
            voice_client = ctx.message.guild.voice_client
            url = self.queue[0]
            async with ctx.typing():
                info = await ydl.dl(url)
                if "url" not in info:
                    if "entries" not in info:
                        await ctx.send("Invalid url: " + url)
                        self.queue.pop(0)
                        return
                    info = info["entries"][0]

                await ctx.send("Now Playing: " + info["title"])
                voice_client.play(discord.FFmpegOpusAudio(info["url"], **FFMPEG_OPTIONS),
                                  after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx, e), self.bot.loop))
                self.queue.pop(0)

    @commands.command()
    async def pause(self, ctx: Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("The bot is not currently playing.")

    @commands.command()
    async def unpause(self, ctx: Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("The bot is not currently paused.")

    @commands.command()
    async def stop(self, ctx: Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            self.queue = []
            voice_client.stop()
        else:
            await ctx.send('The bot is not currently playing.')

    @commands.command()
    async def skip(self, ctx: Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        else:
            await ctx.send('The bot is not currently playing.')

    @commands.command()
    async def nightcore(self, ctx: Context, *args):
        if "off" in args and '-af "asetrate=44100*1.35"' in FFMPEG_OPTIONS["options"]:
            FFMPEG_OPTIONS["options"] = FFMPEG_OPTIONS["options"].replace('-af "asetrate=44100*1.35"', '')
            await ctx.send("Nightcore deactivated.")
            return

        if '-af "asetrate=44100*1.35"' not in FFMPEG_OPTIONS["options"]:
            FFMPEG_OPTIONS["options"] += '-af "asetrate=44100*1.35"'
            await ctx.send("Nightcore activated. 😈")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPlayer(bot))

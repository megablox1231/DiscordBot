import os
import asyncio
import yt_download as ydl

import discord
from discord.ext import commands
from discord.ext.commands import Context


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
    async def play(self, ctx: Context, url: str = None):
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
                await ctx.send("Now Playing: " + info["title"])
                voice_client.play(discord.FFmpegOpusAudio(executable=os.getenv('FFMPEG'), source=info["url"]),
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
            await voice_client.stop()
            self.queue = []
        else:
            await ctx.send('The bot is not currently playing.')

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPlayer(bot))

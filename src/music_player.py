import discord
import os
from discord.ext import commands
from discord.ext.commands import Context


class MusicPlayer(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def test(self, ctx: Context) -> None:
        await ctx.send('Testing')

    @commands.command(help='Tells the bot to join the voice channel')
    async def join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()

    @commands.command(help='To make the bot leave the voice channel')
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command()
    async def play(self, ctx):
        voice_client = ctx.message.guild.voice_client
        async with ctx.typing():
            voice_client.play(discord.FFmpegOpusAudio(executable=os.getenv('FFMPEG'), source='ex.mp3'))
        await ctx.send('Now Playing')

    @commands.command()
    async def pause(self, ctx):
        voice_client = ctx.message.guild.voice_client

    @commands.command()
    async def stop(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.stop()
        else:
            await ctx.send('The bot is not currently playing.')

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPlayer(bot))

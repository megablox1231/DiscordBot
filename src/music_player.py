import discord
from discord.ext import commands
from discord.ext.commands import Context


class MusicPlayer(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def test(self, ctx: Context) -> None:
        await ctx.send('Testing')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPlayer(bot))

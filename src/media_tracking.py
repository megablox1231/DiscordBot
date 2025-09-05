import discord
from discord.ext import commands
from discord.ext.commands import Context

class MediaTracking(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def list(self, ctx: Context):
        media = ""
        nums = []
        with open("media_list.txt", "r") as file:
            for line in file:
                media += line
                nums.append("1 | 1 | 1")

        embed = discord.Embed(title="Watched List", description="This is the watch list of the things you've watched.")
        embed.add_field(name="Name", value=media, inline=True)
        embed.add_field(name="Scores [AKJ]", value='\n'.join(nums), inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def add(self, ctx: Context, media: str):
        pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MediaTracking(bot))
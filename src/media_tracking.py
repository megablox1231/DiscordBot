import csv

import discord
from discord.ext import commands
from discord.ext.commands import Context

class MediaTracking(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def list(self, ctx: Context):
        titles = []
        scores = []

        with open("media_list.csv", "r") as file:
            csv_reader = csv.reader(file)
            next(csv_reader)

            for row in csv_reader:
                titles.append(row[0])
                scores.append('  |  '.join(row[1:]))

        embed = discord.Embed(title="Watched List", description="This is the watch list of the things you've watched.")
        embed.add_field(name="Title", value='\n'.join(titles), inline=True)
        embed.add_field(name="A | J | K", value='\n'.join(scores), inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def add(self, ctx: Context, title: str):
        with open("media_list.csv", "a", newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow([title, "~", "~", "~"])

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MediaTracking(bot))
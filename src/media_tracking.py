import csv
import json

import pandas as pd
import numpy as np

import discord
from discord.ext import commands
from discord.ext.commands import Context


class MediaData:
    def __init__(self):
        self.media_df = pd.read_csv("media_list.csv")
        with open("users.json", "r") as file:
            self.users: dict = json.load(file)

    def save_media_df(self):
        self.media_df.to_csv("media_list.csv")


class MediaTracking(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data = MediaData()

    @commands.command()
    async def list(self, ctx: Context):
        titles = self.data.media_df["title"]
        lists = self.data.media_df.drop("title", axis=1).values.tolist()
        scores = ["  |  ".join([str(x) if not np.isnan(x) else "~" for x in row]) for row in lists]

        embed = discord.Embed(title="Watched List", description="This is the watch list of the things you've watched.")
        embed.add_field(name="Title", value='\n'.join(titles), inline=True)
        embed.add_field(name="A | J | K", value='\n'.join(scores), inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def add(self, ctx: Context, title: str):
        self.data.media_df.loc[len(self.data.media_df)] = ["title"] + [np.nan] * len(self.data.users)
        self.data.save_media_df()

    @commands.command()
    async def register(self, ctx: Context, name: str):
        uid = str(ctx.author.id)

        if uid in self.data.users:
            await ctx.send(f"You are already registered with us as {self.data.users[uid]}!")
        else:
            self.data.users[uid] = name
            with open("users.json", "w") as file:
                json.dump(self.data.users, file, ensure_ascii=False, indent=4)

            self.data.media_df[name] = np.nan
            self.data.save_media_df()
            await ctx.send(f"You have been registered as {name}. Thank you for joining!")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MediaTracking(bot))
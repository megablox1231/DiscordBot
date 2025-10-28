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

    def reload_media_df(self):
        self.media_df = pd.read_csv("media_list.csv")

    def reload_users(self):
        with open("users.json", "r") as file:
            self.users: dict = json.load(file)

    def save_media_df(self):
        self.media_df.to_csv("media_list.csv", index=False)

    def save_users(self):
        with open("users.json", "w") as file:
            json.dump(self.users, file, ensure_ascii=False, indent=4)

    def list(self, uid: str):
        self.reload_media_df()
        self.reload_users()

        titles = self.media_df["title"].tolist()
        for i in range(len(titles)):
            titles[i] = str(i+1) + "\. " + titles[i]
        name = self.users[uid]
        scores = self.media_df[name]
        scores = [str(x) if not np.isnan(x) else "~" for x in scores]

        return titles, scores

    def list_all(self):
        self.reload_media_df()
        self.reload_users()

        titles = self.media_df["title"].tolist()
        for i in range(len(titles)):
            titles[i] = str(i+1) + "\. " + titles[i]
        lists = self.media_df.drop("title", axis=1).values.tolist()
        scores = ["  |  ".join([str(x) if not np.isnan(x) else "~" for x in row]) for row in lists]

        initials = self.media_df.columns.tolist()[1:]
        initials = [name[0] for name in initials]
        initials = " | ".join(initials)

        return titles, scores, initials

    def has_user(self, uid: str):
        self.reload_users()

        return uid in self.users

    def register_user(self, uid: str, name: str):
        self.reload_media_df()
        self.reload_users()

        self.users[uid] = name
        self.save_users()

        self.media_df[name] = np.nan
        self.save_media_df()

    def add_title(self, title: str):
        self.reload_media_df()
        self.reload_users()

        self.media_df.loc[len(self.media_df)] = [title] + [np.nan] * len(self.users)
        self.save_media_df()

    def edit_title(self, index: int, title: str):
        self.reload_media_df()
        self.reload_users()

        self.media_df.loc[index-1, "title"] = title
        self.save_media_df()

    def score(self, uid: str, index: int, score: float):
        self.reload_media_df()
        self.reload_users()

        self.media_df.loc[index-1, self.users[uid]] = score
        self.save_media_df()

class MediaTracking(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data = MediaData()

    @commands.command()
    async def list(self, ctx: Context):
        uid = str(ctx.author.id)

        if not self.data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        titles, scores = self.data.list(uid)

        embed = discord.Embed(title="Watched List", description="This is the list of TV shows and movies you've "
                                                                "watched.")
        embed.add_field(name="Title", value='\n'.join(titles), inline=True)
        embed.add_field(name="Scores", value='\n'.join(scores), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="listall")
    async def list_all(self, ctx: Context):
        titles, scores, initials = self.data.list_all()

        embed = discord.Embed(title="Watched List", description="This is the list of the TV shows and movies you've "
                                                                "watched.")
        embed.add_field(name="Title", value='\n'.join(titles), inline=True)
        embed.add_field(name=initials, value='\n'.join(scores), inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def add(self, ctx: Context, title: str = None):
        if title is None:
            await ctx.send("Please enter a title. Ex: $add Inception")
            return

        self.data.add_title(title)

    @commands.command(name="edittitle")
    async def edit_title(self, ctx: Context, index: int = None, new_title: str = None):
        if index is None or new_title is None:
            await ctx.send("Please enter an index from the Watch List and a title. Ex: $edittitle 2 Inception")
            return

        self.data.edit_title(index, new_title)

    @commands.command()
    async def score(self, ctx: Context, index: int = None, score: float = None):
        if index is None or score is None:
            await ctx.send("Please enter an index from the Watch List and a score. Ex: $score 13 7.8")
            return

        uid = str(ctx.author.id)
        if not self.data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        self.data.score(uid, index, score)

    @commands.command()
    async def register(self, ctx: Context, name: str = None):
        if name is None:
            await ctx.send("Please enter a name to register with. Ex: $register name")
            return

        uid = str(ctx.author.id)

        if self.data.has_user(uid):
            await ctx.send(f"You are already registered with me as {self.data.users[uid]}!")
        else:
            self.data.register_user(uid, name)
            await ctx.send(f"You have been registered as {name}. Thank you for joining!")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MediaTracking(bot))
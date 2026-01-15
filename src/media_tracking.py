import json

import pandas as pd
import numpy as np

import discord
from discord.ext import commands
from discord.ext.commands import Context


class ListAllPaginator(discord.ui.View):
    def __init__(self, ctx, titles: list[str], scores: list[list[str]], initials: list[str], include_avg):
        super().__init__(timeout=120)
        self.ctx = ctx

        self.titles = titles
        self.scores = scores
        self.initials = initials
        self.include_avg = include_avg

        self.page = 0
        self.per_page = 15
        self.max_page = (len(titles) - 1) // self.per_page

        # precalc column widths
        self.title_width = max(len(t) for t in titles)

        # score columns individually padded
        self.score_widths = []
        for col_idx in range(len(initials)):
            max_width = max(len(row[col_idx]) for row in scores)
            max_width = max(max_width, len(initials[col_idx]))
            self.score_widths.append(max_width)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id

    def build_page_text(self):
        start = self.page * self.per_page
        end = start + self.per_page

        lines = []

        # Header
        header_title = "Title".ljust(self.title_width)
        header_scores = " ".join(
            initials.ljust(self.score_widths[i])
            for i, initials in enumerate(self.initials)
        )
        header_line = f"{header_title}  {header_scores}"
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Rows with alternating background
        for i, (t, row_scores) in enumerate(zip(self.titles[start:end], self.scores[start:end])):
            padded_title = t.ljust(self.title_width)

            padded_scores = " ".join(
                row_scores[col_idx].ljust(self.score_widths[col_idx])
                for col_idx in range(len(row_scores))
            )

            line = f"{padded_title}  {padded_scores}"

            if i % 2 == 0:
                line = f"\x1b[40m{line}\x1b[0m"

            lines.append(line)

        return "```ansi\n" + "\n".join(lines) + "\n```"

    def build_embed(self):
        embed = discord.Embed(
            title="Watched List (All Users)",
            description=self.build_page_text()
        )
        embed.set_footer(text=f"Page {self.page+1} / {self.max_page+1}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


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

    def list_all(self, include_avg=False):
        self.reload_media_df()
        self.reload_users()

        # Titles (with numbering only)
        titles = self.media_df["title"].tolist()
        titles = [f"{i+1}. {titles[i]}" for i in range(len(titles))]

        user_columns = self.media_df.columns.tolist()[1:]

        # Initials header for display (raw list, not formatted)
        initials = [name[0].upper() for name in user_columns]

        lists = self.media_df.drop("title", axis=1)

        # Add average column
        if include_avg:
            lists["avg"] = lists.mean(axis=1)
            initials.append("avg")

        scores = []
        for row in lists.values.tolist():
            cleaned = [(str(x) if not np.isnan(x) else "~") for x in row]
            scores.append(cleaned)

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
    async def list_all(self, ctx: Context, *args):
        include_avg = "avg" in args
        titles, scores, initials = self.data.list_all(include_avg)

        paginator = ListAllPaginator(ctx, titles, scores, initials, include_avg)
        embed = paginator.build_embed()

        await ctx.send(embed=embed, view=paginator)

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
import json

import discord
from discord.ext import commands
from discord.ext.commands import Context

from media_tracking import MediaData


class TierListData:

    EMPTY_TIER_LIST = {
        "S" : [],
        "A" : [],
        "B" : [],
        "C" : [],
        "D" : [],
        "F" : []
    }

    def __init__(self) -> None:
        self.tier_lists = {}
        self.load_tier_lists()

    def load_tier_lists(self) -> None:
        with open("tier_lists.json", "r") as file:
            self.tier_lists = json.load(file)

    def save_tier_lists(self) -> None:
        with open("tier_lists.json", "w") as file:
            json.dump(self.tier_lists, file, ensure_ascii=False, indent=4)

    def get_tier_list(self, user_id: str, tier_list_id: str) -> dict:
        self.load_tier_lists()
        if tier_list_id is None:
            tier_list_id = self.tier_lists[user_id]["_currentTierListID"]

        if user_id not in self.tier_lists or tier_list_id not in self.tier_lists[user_id]:
            return {}

        return self.tier_lists[user_id][tier_list_id]

    def add_tier_list(self, user_id: str, tier_list_id: str) -> int:
        self.load_tier_lists()

        if tier_list_id in self.tier_lists[user_id].keys():
            return -1
        else:
            self.tier_lists[user_id][tier_list_id] = self.EMPTY_TIER_LIST
            self.save_tier_lists()
            return 1

    def remove_tier_list(self, user_id: str, tier_list_id: str) -> None:
        self.load_tier_lists()

        self.tier_lists[user_id].pop(tier_list_id)
        self.save_tier_lists()

    def set_tier_list(self, user_id: str, tier_list_id: str) -> None:
        self.load_tier_lists()

        self.tier_lists[user_id]["_currentTierListID"] = tier_list_id
        self.save_tier_lists()

    def rank(self, user_id: str, tier_list_id: str, item: str, tier: str, position: int = -1) -> int:
        self.load_tier_lists()
        if tier_list_id is None:
            tier_list_id = self.tier_lists[user_id]["_currentTierListID"]
        else:
            self.tier_lists[user_id][tier_list_id]["_currentTierListID"] = tier_list_id

        if position == -1:
            self.tier_lists[user_id][tier_list_id][tier].append(item)
            self.save_tier_lists()
            return 1
        elif position <= len(self.tier_lists[user_id][tier_list_id][tier]):
            self.tier_lists[user_id][tier_list_id][tier].insert(position, item)
            self.save_tier_lists()
            return 1
        else:
            self.save_tier_lists()
            return -1

    def derank(self, user_id: str, tier_list_id: str, tier: str, position: int) -> int:
        self.load_tier_lists()
        if tier_list_id is None:
            tier_list_id = self.tier_lists[user_id]["_currentTierListID"]
        else:
            self.tier_lists[user_id][tier_list_id]["_currentTierListID"] = tier_list_id

        if 0 <= position < len(self.tier_lists[user_id][tier_list_id][tier]):
            self.tier_lists[user_id][tier_list_id][tier].pop(position)
            self.save_tier_lists()
            return 1
        else:
            self.save_tier_lists()
            return -1

    def change_rank(self, user_id: str, tier_list_id: str, tier: str,
                    position: int, new_tier: str, new_position: int) -> int:
        self.load_tier_lists()
        if tier_list_id is None:
            tier_list_id = self.tier_lists[user_id]["_currentTierListID"]
        else:
            self.tier_lists[user_id][tier_list_id]["_currentTierListID"] = tier_list_id

        if (0 <= position < len(self.tier_lists[user_id][tier_list_id][tier]) and
                0 <= new_position <= len(self.tier_lists[user_id][tier_list_id][new_tier])):
            item = self.tier_lists[user_id][tier_list_id][tier].pop(position)
            self.tier_lists[user_id][tier_list_id][new_tier].insert(new_position, item)
            self.save_tier_lists()
            return 1
        else:
            self.save_tier_lists()
            return -1

    def has_tier_list(self, user_id: str, tier_list_id: str) -> bool:
        self.load_tier_lists()

        return tier_list_id in self.tier_lists[user_id].keys()


class TierList(commands.Cog):

    TIER_LIST_LABELS = {
        "S" : "🇸",
        "A" : "🇦",
        "B" : "🇧",
        "C" : "🇨",
        "D" : "🇩",
        "F" : "🇫"
    }

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.media_data = MediaData()
        self.tl_data = TierListData()

    @commands.command(name='tierlist', aliases=['tl'])
    async def tier_list(self, ctx: Context, name: str = None) -> None:
        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        tier_list = self.tl_data.get_tier_list(uid, name)
        if tier_list is None:
            await ctx.send(f"Tier list {name} does not exist.")
            return
        if name is not None:
            self.tl_data.set_tier_list(uid, name)

        embed = discord.Embed(title=name)
        for key, value in self.TIER_LIST_LABELS.items():
            embed.add_field(name="-" * 65, value=value + "  " + " | ".join(tier_list[key]), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="addtierlist", aliases=["atl"])
    async def add_tier_list(self, ctx: Context, name: str) -> None:
        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        if self.tl_data.add_tier_list(uid, name) == 1:
            self.tl_data.set_tier_list(uid, name)
            await ctx.send(f"Tier list {name} added.")
        else:
            await ctx.send(f"Tier list {name} already exists.")

    @commands.command(name="removetierlist", aliases=["rtl"])
    async def remove_tier_list(self, ctx: Context, name: str) -> None:
        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        if not self.tl_data.has_tier_list(uid, name):
            await ctx.send(f"Removal failed due to invalid tier list {name}.")
        else:
            self.tl_data.remove_tier_list(uid, name)
            await ctx.send(f"Tier list {name} removed.")

    @commands.command(aliases=["r"])
    async def rank(self, ctx: Context, item: str = None, tier: str = None, position: int = 0, tier_list_name: str = None) -> None:
        if item is None or tier is None:
            await ctx.send('Please enter an item and tier to rank it. Ex: $rank "Hollow Knight" S')

        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return
        if tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if tier_list_name is not None and self.tl_data.has_tier_list(uid, tier_list_name):
            await ctx.send(f"Ranking failed due to invalid tier list {tier_list_name}.")

        result = self.tl_data.rank(uid, tier_list_name, item, tier, position - 1)
        if result == 1:
            await ctx.send(f"{item} added to {tier} tier.")
        else:
            await ctx.send(f"Ranking failed due to invalid position {position}.")

    @commands.command(aliases=["d"])
    async def derank(self, ctx: Context, tier: str = None, position: int = None, tier_list_name: str = None) -> None:
        if position is None or tier is None:
            await ctx.send('Please enter an tier and position to derank it. Ex: $derank "Hollow Knight" S')

        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return
        if tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if tier_list_name is not None and not self.tl_data.has_tier_list(uid, tier_list_name):
            await ctx.send(f"Deranking failed due to invalid tier list {tier_list_name}.")

        result = self.tl_data.derank(uid, tier_list_name, tier, position - 1)
        if result == 1:
            await ctx.send(f"Deranking successful.")
        else:
            await ctx.send(f"Deranking failed due to invalid position {position}.")

    @commands.command(name="changerank", aliases=["cr"])
    async def change_rank(self, ctx: Context, tier: str = None, position: int = None, new_tier: str = None,
                          new_position: int = None,  tier_list_name: str = None) -> None:
        if position is None or tier is None or new_tier is None or new_position is None:
            await ctx.send('Please enter two sets of tiers and positions to change ranks. Ex: $changerank S 3 A 1')

        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return
        if tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if new_tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {new_tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if tier_list_name is not None and not self.tl_data.has_tier_list(uid, tier_list_name):
            await ctx.send(f"Deranking failed due to invalid tier list {tier_list_name}.")
            return

        if self.tl_data.change_rank(uid, tier_list_name, tier, position-1, new_tier, new_position-1) == 1:
            await ctx.send(f"Rank change successful.")
        else:
            await ctx.send(f"Rank change failed due to invalid set of positions {position}, {new_position}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TierList(bot))
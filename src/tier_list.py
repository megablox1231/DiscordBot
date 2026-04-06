import json
import io
import asyncio
import math
from typing import Optional
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from jikanpy import AioJikan

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
        with open("tier_lists.json", "r", encoding="utf-8") as file:
            self.tier_lists = json.load(file)

    def save_tier_lists(self) -> None:
        with open("tier_lists.json", "w", encoding="utf-8") as file:
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

    def rank(self, user_id: str, tier_list_id: str, item: dict, tier: str, position: int = -1) -> int:
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


class TierListImageGenerator:
    """Generates a tier list image using PIL."""

    TIER_COLORS = {
        "S": (255, 127, 127),   # Red / salmon
        "A": (255, 191, 127),   # Orange
        "B": (255, 255, 127),   # Yellow
        "C": (127, 255, 127),   # Green
        "D": (127, 191, 255),   # Blue
        "F": (199, 127, 255),   # Purple
    }

    TILE_SIZE = 150          # Each item image is this many px square
    LABEL_WIDTH = 150        # Width of the tier label column
    NAME_HEIGHT = 28         # Height for name text below each tile
    ITEMS_PER_ROW = 10       # Max items before wrapping to next row
    PADDING = 4              # Gap between tiles
    BG_COLOR = (30, 30, 30)  # Dark background
    BORDER_COLOR = (10, 10, 10)

    def __init__(self) -> None:
        # Try to load a TTF font for tier labels
        try:
            self.font = ImageFont.truetype("arial.ttf", 60)
        except OSError:
            try:
                self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            except OSError:
                self.font = ImageFont.load_default()

        # Smaller font for item names below tiles
        try:
            self.name_font = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            try:
                self.name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except OSError:
                self.name_font = ImageFont.load_default()

    def _get_tier_row_count(self, item_count: int) -> int:
        """Calculate how many rows a tier needs."""
        if item_count == 0:
            return 1
        return math.ceil(item_count / self.ITEMS_PER_ROW)

    def _truncate_name(self, name: str, max_width: int) -> str:
        """Truncate name to fit within max_width pixels."""
        bbox = self.name_font.getbbox(name)
        if bbox[2] - bbox[0] <= max_width:
            return name

        ellipsis = "…"
        for length in range(len(name) - 1, 0, -1):
            truncated = name[:length].rstrip() + ellipsis
            bbox = self.name_font.getbbox(truncated)
            if bbox[2] - bbox[0] <= max_width:
                return truncated
        return ellipsis

    async def _download_image(self, session: aiohttp.ClientSession, url: str) -> Optional[Image.Image]:
        """Download an image from a URL and return a PIL Image."""
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:
            pass
        return None

    async def generate(self, tier_list: dict, title: str = "Tier List") -> io.BytesIO:
        """
        Build the full tier list image.
        Each item is either a dict {"name": str, "image_url": str, ...} or a plain string (legacy).
        Returns a BytesIO PNG buffer.
        """
        tiers_ordered = ["S", "A", "B", "C", "D", "F"]
        item_row_height = self.TILE_SIZE + self.NAME_HEIGHT + self.PADDING

        # Calculate dimensions
        total_height = self.PADDING
        for tier_key in tiers_ordered:
            items = tier_list.get(tier_key, [])
            num_rows = self._get_tier_row_count(len(items))
            total_height += num_rows * item_row_height + self.PADDING

        # Width accommodates ITEMS_PER_ROW tiles
        img_width = (self.LABEL_WIDTH + self.PADDING +
                     self.ITEMS_PER_ROW * (self.TILE_SIZE + self.PADDING))
        img_width = max(img_width, 600)
        img_height = total_height

        image = Image.new("RGBA", (img_width, img_height), self.BG_COLOR)
        draw = ImageDraw.Draw(image)

        # Retrieve all cover images
        cover_cache: dict[str, Image.Image] = {}
        urls_to_fetch: dict[str, str] = {}
        for t in tiers_ordered:
            for item in tier_list.get(t, []):
                if isinstance(item, dict) and item.get("image_url"):
                    mal_id = item["image_url"]
                    mal_id = item["mal_id"]
                    if Path("imageCache/" + str(mal_id) + ".png").exists():
                        cover_cache[mal_id] = Image.open("imageCache/" + str(mal_id) + ".png")
                    elif mal_id not in urls_to_fetch:
                        urls_to_fetch[mal_id] = mal_id

        if urls_to_fetch:
            async with aiohttp.ClientSession() as session:
                tasks = [self._download_image(session, url) for url in urls_to_fetch]
                results = await asyncio.gather(*tasks)
                for mal_id, img in zip(urls_to_fetch, results):
                    if img is not None:
                        cover_cache[urls_to_fetch[mal_id]] = img
                        img.save("imageCache/" + str(urls_to_fetch[mal_id]) + ".png")


        # Draw tiers
        y = self.PADDING
        for tier_key in tiers_ordered:
            color = self.TIER_COLORS[tier_key]
            items = tier_list.get(tier_key, [])
            num_rows = self._get_tier_row_count(len(items))
            tier_total_height = num_rows * item_row_height

            # Draw tier label spanning all rows for this tier
            draw.rectangle(
                [0, y, self.LABEL_WIDTH - 1, y + tier_total_height - 1],
                fill=color,
                outline=self.BORDER_COLOR,
                width=2
            )
            # Center the tier letter vertically and horizontally
            bbox = self.font.getbbox(tier_key)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = (self.LABEL_WIDTH - tw) // 2
            ty = y + (tier_total_height - th) // 2 - bbox[1]
            draw.text((tx, ty), tier_key, fill=(0, 0, 0), font=self.font)

            # Draw items in rows
            row_y = y
            for row_idx in range(num_rows):
                start_idx = row_idx * self.ITEMS_PER_ROW
                end_idx = min(start_idx + self.ITEMS_PER_ROW, len(items))
                row_items = items[start_idx:end_idx]

                x = self.LABEL_WIDTH + self.PADDING
                for item in row_items:
                    if isinstance(item, dict):
                        mal_id = item.get("mal_id", "")
                        name = item.get("name", "?")
                    else:
                        mal_id = ""
                        name = str(item)

                    # Draw tile
                    tile: Optional[Image.Image] = None
                    if mal_id and mal_id in cover_cache:
                        tile = cover_cache[mal_id].copy()
                        tile = tile.resize((self.TILE_SIZE, self.TILE_SIZE), Image.LANCZOS)

                    if tile:
                        image.paste(tile, (x, row_y), tile)
                    else:
                        # Fallback: draw a grey square with the name text inside
                        draw.rectangle(
                            [x, row_y, x + self.TILE_SIZE - 1, row_y + self.TILE_SIZE - 1],
                            fill=(60, 60, 60),
                            outline=self.BORDER_COLOR,
                            width=1
                        )

                        try:
                            fallback_font = ImageFont.truetype("arial.ttf", 16)
                        except OSError:
                            try:
                                fallback_font = ImageFont.truetype(
                                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16
                                )
                            except OSError:
                                fallback_font = ImageFont.load_default()
                        display_name = name if len(name) <= 18 else name[:16] + "…"
                        nbbox = fallback_font.getbbox(display_name)
                        ntw = nbbox[2] - nbbox[0]
                        nth = nbbox[3] - nbbox[1]
                        draw.text(
                            (x + (self.TILE_SIZE - ntw) // 2, row_y + (self.TILE_SIZE - nth) // 2),
                            display_name,
                            fill=(255, 255, 255),
                            font=fallback_font
                        )

                    # Draw name below tile
                    truncated_name = self._truncate_name(name, self.TILE_SIZE - 4)
                    name_bbox = self.name_font.getbbox(truncated_name)
                    name_w = name_bbox[2] - name_bbox[0]
                    name_x = x + (self.TILE_SIZE - name_w) // 2
                    name_y = row_y + self.TILE_SIZE + 2
                    draw.text(
                        (name_x, name_y),
                        truncated_name,
                        fill=(255, 255, 255),
                        font=self.name_font
                    )

                    x += self.TILE_SIZE + self.PADDING

                row_y += item_row_height

            y += tier_total_height + self.PADDING

        # Save to buffer
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf



class AnimeSearcher:
    """Search anime via Jikan (MyAnimeList) and return selection options."""

    @staticmethod
    async def search(query: str, limit: int = 5) -> list[dict]:
        """
        Returns a list of dicts:
        [{"mal_id": int, "title": str, "image_url": str}, ...]
        """
        async with AioJikan() as jikan:
            result = await jikan.search("anime", query, page=1)

        entries = result.get("data", [])[:limit]
        options = []
        for entry in entries:
            title = entry.get("title", "Unknown")
            mal_id = entry.get("mal_id", 0)
            images = entry.get("images", {})
            jpg = images.get("jpg", {})
            image_url = jpg.get("large_image_url") or jpg.get("image_url", "")
            options.append({
                "mal_id": mal_id,
                "title": title,
                "image_url": image_url
            })
        return options


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
        self.image_gen = TierListImageGenerator()

    @commands.command(name='tierlist', aliases=['tl'])
    async def tier_list(self, ctx: Context, name: str = None) -> None:
        """Set and display the current tier list in use."""
        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return

        tier_list = self.tl_data.get_tier_list(uid, name)
        if not tier_list:
            await ctx.send(f"Tier list {name} does not exist.")
            return
        if name is not None:
            self.tl_data.set_tier_list(uid, name)

        display_name = name or self.tl_data.tier_lists[uid].get("_currentTierListID", "Tier List")
        buf = await self.image_gen.generate(tier_list, display_name)
        file = discord.File(buf, filename="tier_list.png")
        embed = discord.Embed(title=display_name)
        embed.set_image(url="attachment://tier_list.png")

        await ctx.send(embed=embed, file=file)

    @commands.command(name="addtierlist", aliases=["atl"])
    async def add_tier_list(self, ctx: Context, name: str) -> None:
        """Create a new tier list."""
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
        """Remove a tier list."""
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
        """Place an item on the current tier list."""
        if item is None or tier is None:
            await ctx.send('Please enter an item and tier to rank it. Ex: $rank "Hollow Knight" S')

        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return
        if tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if tier_list_name is not None and not self.tl_data.has_tier_list(uid, tier_list_name):
            await ctx.send(f"Ranking failed due to invalid tier list {tier_list_name}.")
            return

        chosen = await self._search_and_pick(ctx, item)
        if chosen is None:
            return

        result = self.tl_data.rank(uid, tier_list_name, chosen, tier, position - 1)
        if result == 1:
            await ctx.send(f"{item} added to {tier} tier.")
        else:
            await ctx.send(f"Ranking failed due to invalid position {position}.")

    @commands.command(aliases=["d"])
    async def derank(self, ctx: Context, tier: str = None, position: int = None, tier_list_name: str = None) -> None:
        """Remove an item from the current tier list."""
        if position is None or tier is None:
            await ctx.send('Please enter an tier and position to derank it. Ex: $derank S 1')
            return

        uid = str(ctx.author.id)

        if not self.media_data.has_user(uid):
            await ctx.send("You are not registered with me!")
            return
        if tier not in self.TIER_LIST_LABELS.keys():
            await ctx.send(f"Tier {tier} does not exist. Available Tiers: S, A, B, C, D, F")
            return
        if tier_list_name is not None and not self.tl_data.has_tier_list(uid, tier_list_name):
            await ctx.send(f"Deranking failed due to invalid tier list {tier_list_name}.")
            return

        result = self.tl_data.derank(uid, tier_list_name, tier, position - 1)
        if result == 1:
            await ctx.send(f"Deranking successful.")
        else:
            await ctx.send(f"Deranking failed due to invalid position {position}.")

    @commands.command(name="changerank", aliases=["cr"])
    async def change_rank(self, ctx: Context, tier: str = None, position: int = None, new_tier: str = None,
                          new_position: int = None,  tier_list_name: str = None) -> None:
        """Change the rank of an item on the current tier list."""
        if position is None or tier is None or new_tier is None or new_position is None:
            await ctx.send('Please enter two sets of tiers and positions to change ranks. Ex: $changerank S 3 A 1')
            return

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
            await ctx.send(f"Rank change failed due to invalid tier list {tier_list_name}.")
            return

        if self.tl_data.change_rank(uid, tier_list_name, tier, position-1, new_tier, new_position-1) == 1:
            await ctx.send(f"Rank change successful.")
        else:
            await ctx.send(f"Rank change failed due to invalid set of positions {position}, {new_position}.")

    async def _search_and_pick(self, ctx: Context, query: str) -> Optional[dict]:
        """
        Search for an anime by query, present up to 5 options, wait for the
        user to pick one. Returns the chosen item dict or None on timeout/cancellation.
        """
        results = await AnimeSearcher.search(query, limit=5)
        if not results:
            await ctx.send(f"No results found for **{query}**.")
            return None

        lines = [f"**Search results for** \"{query}\":\n"]
        for i, r in enumerate(results, start=1):
            lines.append(f"`{i}.` {r['title']}  (MAL ID: {r['mal_id']})")
        lines.append("\nReply with the **number** of the correct anime (or `cancel`).")

        await ctx.send("\n".join(lines))

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Selection timed out.")
            return None

        content = reply.content.strip().lower()
        if content == "cancel":
            await ctx.send("Cancelled.")
            return None

        if not content.isdigit() or not (1 <= int(content) <= len(results)):
            await ctx.send("Invalid selection.")
            return None

        choice = results[int(content) - 1]
        return {
            "name": choice["title"],
            "image_url": choice["image_url"],
            "mal_id": choice["mal_id"]
        }


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TierList(bot))
import json

from discord.ext import commands
from discord.ext.commands import Context


class UserData:
    def __init__(self):
        with open("users.json", "r") as file:
            self.users: dict = json.load(file)

    def load_users(self):
        with open("users.json", "r") as file:
            self.users: dict = json.load(file)

    def save_users(self):
        with open("users.json", "w") as file:
            json.dump(self.users, file, ensure_ascii=False, indent=4)

    def has_user(self, uid: str) -> bool:
        self.load_users()
        return uid in self.users

    def get_name(self, uid: str) -> str:
        self.load_users()
        return self.users.get(uid, None)

    def register_user(self, uid: str, name: str):
        self.load_users()
        self.users[uid] = name
        self.save_users()


class Registration(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data = UserData()

    @commands.command()
    async def register(self, ctx: Context, name: str = None):
        """Register yourself with the bot. $register <name>
        ---
        name: the display name to register with (text)
        ---
        $register Alice
        """
        if name is None:
            await ctx.send("Enter a name to register with. For example, `$register Alice`.")
            return

        uid = str(ctx.author.id)

        if self.data.has_user(uid):
            await ctx.send(f"You are already registered with me as {self.data.get_name(uid)}!")
        else:
            self.data.register_user(uid, name)
            self.bot.dispatch("user_register", uid, name)
            await ctx.send(f"You have been registered as {name}. Thank you for joining!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Registration(bot))

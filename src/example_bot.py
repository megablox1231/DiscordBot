import os
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True


class MyBot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(command_prefix='$', intents=intents)

    async def on_ready(self) -> None:
        print(f'We have logged in as {self.user}')

    async def setup_hook(self) -> None:
        await self.load_extension('music_player')

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        if message.content.startswith('$hello'):
            await message.channel.send('Hello!')

        await self.process_commands(message)


load_dotenv()

client = MyBot()
client.run(os.getenv('DISCORD_TOKEN'))

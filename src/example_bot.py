import os
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True


class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix='$', intents=intents)

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('$hello'):
            await message.channel.send('Hello!')

        await self.process_commands(message)

    @commands.command('test')
    async def test(self, ctx):
        ctx.send('Testing')


load_dotenv()

client = MyBot()
client.run(os.getenv('DISCORD_TOKEN'))

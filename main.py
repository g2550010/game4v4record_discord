import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# 環境変数読み込み
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intent設定
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Botインスタンス
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready.")



async def load_cogs():
    await bot.load_extension("register")
    await bot.load_extension("stats")
    await bot.load_extension("match")
    await bot.load_extension("lobby")
    await bot.start(TOKEN)


if __name__ == '__main__':
    asyncio.run(load_cogs())

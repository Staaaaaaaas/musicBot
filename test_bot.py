import logging
from discord.ext import commands
import config

cfg = config.load_config()

bot = commands.Bot(command_prefix=cfg["prefix"])

@bot.event
async def on_ready():
    logging.info("Logged in as %s\n ------------------", bot.user.name)

COGS = ["cogs.music", "cogs.error"]

def add_cogs(client: commands.Bot):
    for cog in COGS:
        client.load_extension(cog)

def run():
    add_cogs(bot)
    bot.run(cfg["token"])

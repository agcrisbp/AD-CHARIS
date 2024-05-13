import discord, os, locale
from discord.ext import commands
from discord.ext.commands import CommandNotFound
from decouple import config

locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or('.'), intents=intents, help_command=None)


def load_cogs():
    return [
        bot.load_extension(f"cogs.{folder}.__init__")
        for folder in os.listdir("cogs")
        if not "." in folder
    ]

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        default_prefix = ('!', '.')
        await ctx.send(f'> Perintah tidak ditemukan. {default_prefix[0]}help', delete_after=10)

if __name__ == "__main__":
    load_cogs()

    # DONT FORGET TO EDIT THIS
    bot.run(config("BOT_TOKEN"))

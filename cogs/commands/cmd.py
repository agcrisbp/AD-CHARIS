import discord
from cogs.commands.umum import Umum
from cogs.commands.mods import Mods
from cogs.commands.owners import Owners
from cogs.commands.prayers import Prayers
from cogs.commands.radio import Radio
from cogs.commands.help import Help



def setup(bot: discord.Bot):
    bot.add_cog(Umum(bot))
    bot.add_cog(Mods(bot))
    bot.add_cog(Owners(bot))
    bot.add_cog(Prayers(bot))
    bot.add_cog(Radio(bot))
    bot.add_cog(Help(bot))

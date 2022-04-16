import discord
from discord.ext import commands

from const import COMMAND_PREFIX
from private import TOKEN
from events import BotEvents, BotStartEvents, locks
from comms import BotActionCommands, BotDisplayCommands

if __name__ == "__main__":
    intents = discord.Intents().all()
    bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
    bot.add_cog(BotEvents(bot))
    bot.add_cog(BotStartEvents(bot))
    bot.add_cog(BotActionCommands(bot))
    bot.add_cog(BotDisplayCommands(bot))
    bot.run(TOKEN)

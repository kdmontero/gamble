from __future__ import annotations

import discord
from discord.ext import commands
from discord.ext.commands import HelpCommand

from const import COMMAND_PREFIX
from private import TOKEN
from events import BotEvents, BotStartEvents, CommandEvents, locks
from commands import Action, Display
from custom_help import CustomHelpCommand

if __name__ == "__main__":
    intents = discord.Intents().all()
    bot = commands.Bot(
        command_prefix=COMMAND_PREFIX,
        intents=intents,
        case_insensitive=True
    )
    bot.add_cog(BotEvents(bot))
    bot.add_cog(BotStartEvents(bot))
    bot.add_cog(CommandEvents(bot))
    bot.add_cog(Action(bot))
    bot.add_cog(Display(bot))
    bot.help_command = CustomHelpCommand()
    bot.run(TOKEN)

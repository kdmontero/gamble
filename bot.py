from __future__ import annotations

import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import HelpCommand

from const import COMMAND_PREFIX
from private import TOKEN
from events import BotEvents, BotStartEvents, CommandEvents, locks
from commands import Action, Display
from help import CustomHelp

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    case_insensitive=True
)
bot.help_command = CustomHelp()

async def load():
    await bot.add_cog(BotEvents(bot))
    await bot.add_cog(BotStartEvents(bot))
    await bot.add_cog(CommandEvents(bot))
    await bot.add_cog(Action(bot))
    await bot.add_cog(Display(bot))

async def main():
    await load()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

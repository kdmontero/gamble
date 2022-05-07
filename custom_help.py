from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import MinimalHelpCommand, DefaultHelpCommand, HelpCommand

if TYPE_CHECKING:
    from discord.ext.commands import Command

class CustomHelpCommand(DefaultHelpCommand):
    def get_command_signature(self, command: Command) -> None:
        return f'{self.clean_prefix}{command.qualified_name} {command.signature}'



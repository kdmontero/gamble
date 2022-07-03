from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from const import COMMAND_PREFIX
import discord
from discord.ext import commands
from discord.ext.commands import MinimalHelpCommand, DefaultHelpCommand, HelpCommand
from pretty_help import PrettyHelp 
from pretty_help.pretty_help import Paginator

if TYPE_CHECKING:
    from discord.ext.commands import Command

class CustomPaginator(Paginator):
    def __init__(self, show_index, color=0):
        self.opening_note = 'Hello there, use prefix $'
        super().__init__(show_index, color)


    def add_cog(
        self, 
        title: commands.Cog, 
        commands_list: List[commands.Command]
    ):
        """
        Add a cog page to the help menu
        Args:
            title (commands.Cog): The title of the embed
            commands_list (List[commands.Command]): List of commands
        """
        if not commands_list:
            return

        page_title = title.qualified_name
        embed = self._new_page(page_title, "")
        self._add_command_fields(embed, page_title, commands_list)


    def add_index(self, title: str, bot: commands.Bot):

        if self.show_index:
            index = self._new_page(title=title, description=self.opening_note)

            for page_no, page in enumerate(self._pages, 1):
                content = ", ".join([i.name for i in page.fields])

                index.add_field(
                    name=f"{page_no}) {page.title}",
                    value=f'{self.prefix}{content}{self.suffix}',
                    inline=False,
                )
            index.set_footer(text=self.ending_note)
            self._pages.insert(0, index)

        else:
            self._pages[0].description = bot.description


class CustomHelpCommand(PrettyHelp):
    def __init__(self, **options):
        super().__init__(**options)
        self.paginator = CustomPaginator(color=self.color, show_index=options.pop('show_index', True))


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

class HelpPaginator(Paginator):
    def __init__(self, show_index, color=0):
        self.opening_note = f'use prefix `{COMMAND_PREFIX}` before a command.'
        super().__init__(show_index, color)
        self.prefix = self.suffix = '`'


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


    @staticmethod
    def __command_info(command: Union[commands.Command, commands.Group]):
        info = ""
        if command.brief:
            info += command.brief + "\n\n"
        if not info:
            info = ""
        return info

    def add_command(self, command: commands.Command, signature: str):
        """
        Add a command help page
        Args:
            command (commands.Command): The command to get help for
            signature (str): The command signature/usage string
        """
        prefix_command = f'{COMMAND_PREFIX}{command.qualified_name}'
        page = self._new_page(
            prefix_command,
            f"{self.__command_info(command)}" or "",
        )

        
        usage = ' ' + command.usage if command.usage else ""
        page.add_field(
            name="Usage", value=f"{self.prefix}{prefix_command}{usage}{self.suffix}", inline=True
        )
        aliases = command.aliases
        if aliases:
            page.add_field(
                name="Aliases", value=f"{self.prefix}{''.join(aliases)}{self.suffix}", inline=False
            )

        self._add_page(page)


    def add_index(self, title: str, bot: commands.Bot):

        if self.show_index:
            index = self._new_page(title=title, description=self.opening_note)

            for page_no, page in enumerate(self._pages, 1):
                content = " | ".join([i.name for i in page.fields])

                index.add_field(
                    name=f"{page_no}) {page.title}",
                    value=f'{self.prefix}{content}{self.suffix}',
                    inline=False,
                )
            index.set_footer(text=self.ending_note)
            self._pages.insert(0, index)

        else:
            self._pages[0].description = bot.description


class CustomHelp(PrettyHelp):
    def __init__(self, **options):
        super().__init__(**options)
        self.paginator = HelpPaginator(color=self.color, show_index=options.pop('show_index', True))
        self.ending_note = (
            "<required input> [optional input]\n"
            "Type `{help.clean_prefix}{help.invoked_with} command` for more info on a command.\n"
            "You can also type `{help.clean_prefix}{help.invoked_with} category` for more info on a category."
        )
        


    async def command_callback(self, ctx, /, *, command=None) -> None:
        """|coro|
        The actual implementation of the help command.
        It is not recommended to override this method and instead change
        the behaviour through the methods that actually get dispatched.
        - :meth:`send_bot_help`
        - :meth:`send_cog_help`
        - :meth:`send_group_help`
        - :meth:`send_command_help`
        - :meth:`get_destination`
        - :meth:`command_not_found`
        - :meth:`subcommand_not_found`
        - :meth:`send_error_message`
        - :meth:`on_help_command_error`
        - :meth:`prepare_help_command`
        .. versionchanged:: 2.0
            ``ctx`` parameter is now positional-only.
        """

        bot = ctx.bot

        if command is None:
            await self.prepare_help_command(ctx, command)
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        await self.prepare_help_command(ctx, command.lower())


        # Check if it's a cog
        cog = bot.get_cog(command.title())
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.lower().split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)  # type: ignore
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)



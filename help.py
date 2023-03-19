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
        self.prefix = self.suffix = ''


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

        page_title = f'{title.qualified_name} Commands'
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

        if command.usage:
            args = command.usage.strip().splitlines()
            if args[0] == 'no args':
                args[0] = ''
            usage_list = [prefix_command + ' ' + arg.strip() for arg in args]
            usage_body = '\n'.join(usage_list)
        else:
            usage_body = prefix_command

        page.add_field(
            name="Usage", value=usage_body, inline=True
        )

        aliases = command.aliases
        if aliases:
            page.add_field(
                name="Aliases", value=f"{''.join(aliases)}", inline=False
            )

        self._add_page(page, True)


    def _add_page(self, page: discord.Embed, command: bool=False):
        """
        Add a page to the paginator
        Args:
            page (discord.Embed): The page to add
            command (bool): True for command pages 
        """
        if command:
            page_footer = (
                "Note: <required input> [optional input]\n" + self.ending_note
            )
        else:
            page_footer = self.ending_note

        page.set_footer(text=page_footer)
        self._pages.append(page)


class CustomHelp(PrettyHelp):
    def __init__(self, **options):
        super().__init__(**options)
        self.paginator = HelpPaginator(color=self.color, show_index=options.pop('show_index', True))
        self.ending_note = (
            "Type `{help.clean_prefix}{help.invoked_with} <command>` for more info on a command.\n"
            "You can also type `{help.clean_prefix}{help.invoked_with} <category>` for more info on a category."
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



    async def send_bot_help(self, mapping: dict):
        bot = self.context.bot
        channel = self.get_destination()
        async with channel.typing():
            mapping = {name: [] for name in mapping}
            help_filtered = (
                filter(lambda c: c.name != "help", bot.commands)
                if len(bot.commands) > 1
                else bot.commands
            )
            for cmd in await self.filter_commands(
                help_filtered,
                sort=self.sort_commands,
            ):
                mapping[cmd.cog].append(cmd)

            # filter out the empty cog and empty command_list
            mapping = {cog: command_list for cog, command_list in mapping.items() if (command_list and cog)}
            sorted_map = sorted(
                mapping.items(),
                key=lambda cg: cg[0].qualified_name
                if isinstance(cg[0], commands.Cog)
                else str(cg[0]),
            )

        title = self.index_title
        description = self.paginator.opening_note
        index = self.paginator._new_page(title=title, description=description)

        for page_no, (cog, command_list) in enumerate(sorted_map, 1):
            content = " | ".join([cmd.name for cmd in command_list])

            index.add_field(
                name=f"{page_no}) {cog.qualified_name}",
                value=f'{content}',
                inline=False,
            )
        index.set_footer(text=self.paginator.ending_note)
        self.paginator._pages = [index]

        await self.send_pages()

from __future__ import annotations

import json
import os
import asyncio
from time import localtime, strptime, strftime, mktime

from collections import OrderedDict
from random import randint, choice
from typing import TYPE_CHECKING, Optional

import discord # pip install discord
from discord.ext import commands

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD, PATH
from events import locks, refresh_data
from events import BotEvents
from custom_help import CustomHelpCommand
from errors import (
    NotEnoughCoinsError, 
    InvalidAmountError, 
    InvalidNameError,
    RewardError,
    TransactionPairError,
    DataNotFound,
)

from discord.guild import Guild
from discord.member import Member
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context


class Action(commands.Cog):
    '''gamble, yolo, claim, send, refresh'''

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        '''
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self
        '''

    '''
    def cog_unload(self) -> None:
        self.bot.help_command = self. _original_help_command
    '''


    @commands.command()
    async def ping(self, ctx: Context) -> None:
        await ctx.channel.send("pong")


    @commands.command(aliases=['r'])
    async def refresh(self, ctx: Context) -> None:
        '''refresh the \ndata'''
        refresh_data(ctx.guild)
        # self.bot.dispatch('guild_join', ctx.guild)
        await ctx.channel.send("`Data refreshed!`")


    @commands.command(aliases=['g'])
    async def gamble(self, 
        ctx: Context, 
        amount: str, 
        opponent_name: Optional[str] = None
    ) -> None:
        '''
        gamble all
            - gamble all coins

        gamble <amount>
            - gamble a certain amount of coins

        gamble <amount> <opponent_name>
            - gamble a certain amount vs. another member
        '''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()
            
            gambler = data['members'][str(ctx.author.id)]
            coins = gambler['coins']
            
            result = choice(['win', 'loss'])
            
            if amount == 'all':
                bet = coins
            else:
                try:
                    bet = int(amount)
                except ValueError:
                    raise InvalidAmountError()

            if bet > coins:
                raise NotEnoughCoinsError(ctx.author.display_name, coins)
            elif bet <= 0:
                raise InvalidAmountError()


            if opponent_name is not None:
                opponent = None
                for member in data['members'].values():
                    if opponent_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        opponent = member
                        break

                if opponent is None or opponent == gambler:
                    raise InvalidNameError()

                if bet > opponent['coins']:
                    raise NotEnoughCoinsError(opponent['display_name'], opponent['coins'])

                if result == 'win':
                    winner = gambler
                    loser = opponent
                else:
                    winner = opponent
                    loser = gambler

                winner['coins'] += bet
                winner['wins'] += 1
                loser['coins'] -= bet
                loser['losses'] += 1

                if str(loser['id']) in winner['wins_per_mem']:
                    winner['wins_per_mem'][str(loser['id'])] += 1
                else:
                    winner['wins_per_mem'][str(loser['id'])] = 1

                if str(winner['id']) in loser['losses_per_mem']:
                    loser['losses_per_mem'][str(winner['id'])] += 1
                else:
                    loser['losses_per_mem'][str(winner['id'])] = 1

                await ctx.channel.send(f"{winner['display_name']} won!")

            else: 
                if result == 'win':
                    gambler['coins'] += bet
                    gambler['wins'] += 1
                    await ctx.channel.send(f"Noice! {ctx.author.display_name} won {bet} coins! You now have {gambler['coins']} coins")

                elif result == 'loss':
                    gambler['coins'] -= bet
                    gambler['losses'] += 1
                    await ctx.channel.send(f"Sorry, {ctx.author.display_name} lost {bet} coins. Only {gambler['coins']} coins left")

            with open(f"{PATH}{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command(aliases=['y'])
    async def yolo(self, ctx: Context) -> None:
        '''Same command as gamble all'''
        await ctx.invoke(self.bot.get_command('gamble'), amount='all')


    @commands.command(aliases=['c'])
    async def claim(self, ctx: Context) -> None:
        '''
        Claim a random amount of rewards (between MIN_REWARD and MAX_REWARD)
        '''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()

            gambler = data['members'][str(ctx.author.id)]
            
            time_claimed = strptime(
                gambler['last_claimed'],
                '%d %b %Y %H:%M:%S'
            )
            interval = mktime(localtime()) - mktime(time_claimed)
            remaining_mins = int(60 - (interval // 60))

            if remaining_mins > 0:
                raise RewardError(remaining_mins)

            rewards = randint(MIN_REWARD, MAX_REWARD)
            gambler['coins'] += rewards
            time_stamp = strftime('%d %b %Y %H:%M:%S', localtime())
            gambler['last_claimed'] = time_stamp
            await ctx.channel.send(f"{gambler['display_name']} claimed {rewards} coins! You now have {gambler['coins']} coins")
            
            with open(f"{PATH}{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)
    

    @commands.command(aliases=['s'])
    async def send(self, ctx: Context, amount: str, receiver_name: str) -> None:
        '''Send coins to other user'''
        async with locks[ctx.guild.id]:
            try:
                amount = int(amount)
            except ValueError:
                raise InvalidAmountError()

            if amount < 1:
                raise InvalidAmountError()

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()

            sender = data['members'][str(ctx.author.id)]

            if sender['coins'] < amount:
                raise NotEnoughCoinsError(ctx.author.display_name, sender['coins'])

            receiver = None
            for member in data['members'].values():
                if receiver_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                    receiver = member
                    break
            
            if sender == receiver or receiver is None:
                raise InvalidNameError()
            
            sender['coins'] -= amount
            sender['transfers'] += amount
            receiver['coins'] += amount
            receiver['transfers'] -= amount
            
            if str(receiver['id']) in sender['transfers_per_mem']:
                sender['transfers_per_mem'][str(receiver['id'])] += amount
            else:
                sender['transfers_per_mem'][str(receiver['id'])] = amount

            if str(sender['id']) in receiver['transfers_per_mem']:
                receiver['transfers_per_mem'][str(sender['id'])] -= amount
            else:
                receiver['transfers_per_mem'][str(sender['id'])] = -amount

            await ctx.channel.send(f"{sender['display_name']} transferred {amount} coins to {receiver['display_name']}")

            with open(f"{PATH}{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)



class Display(commands.Cog):
    '''wallet, score, transfers'''

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.command(aliases=['w'])
    async def wallet(
        self, 
        ctx: Context, 
        gambler_name: Optional[str] = None
    ) -> None:
        '''Shows the current amount of coins'''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()

            if gambler_name == 'all':
                content = ""
                for member in data['members'].values():
                    if ctx.guild.get_member(member['id']) is not None:
                        content += f"{member['display_name']}: {member['coins']} coins\n"
                await ctx.channel.send(content)

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members'].values():
                    if gambler_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        coins = member['coins']
                        await ctx.channel.send(f"{gambler_name}: {coins} coins")
                        return

                raise InvalidNameError()


    @commands.command(aliases=['sc'])
    async def score(
        self, 
        ctx: Context, 
        gambler_name: Optional[str] = None, 
        opponent_name: Optional[str] = None
    ) -> None:
        '''Shows the win-loss score'''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()

            if gambler_name == 'all' and opponent_name is None:
                content = ""
                for member in data['members'].values():
                    if ctx.guild.get_member(member['id']) is not None:
                        content += f"{member['display_name']}: {member['wins']} W - {member['losses']} L\n"
                await ctx.channel.send(content)
                return
            
            gambler = None
            if gambler_name is None:
                gambler = data['members'][str(ctx.author.id)]
            else:
                for member in data['members'].values():
                    if gambler_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        gambler = member
                        break

            if gambler is None:
                raise InvalidNameError()

            if opponent_name is None:
                wins = gambler['wins']
                losses = gambler['losses']
                await ctx.channel.send(f"{gambler['display_name']}: {wins} W - {losses} L")
                return

            elif opponent_name == 'all':
                if len(gambler['wins_per_mem']) == 0:
                    raise TransactionPairError(gambler['display_name'], 'other members', 'score')

                content = f"{gambler['display_name']} scores:\n"
                for other_id in gambler['wins_per_mem']:
                    other = data['members'][other_id]
                    other_name = other['display_name']
                    other_score = gambler['losses_per_mem'][other_id]
                    gambler_score = gambler['wins_per_mem'][other_id]
                    content += f"{gambler_score} - {other_score} {other_name}"

                await ctx.channel.send(content)
                return

            else:
                opponent = None
                for member in data['members'].values():
                    if opponent_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        opponent = member

                if opponent is None:
                    raise InvalidNameError()

            try:
                gambler_score = gambler['wins_per_mem'][str(opponent['id'])]
                opponent_score = gambler['losses_per_mem'][str(opponent['id'])]
            except KeyError:
                raise TransactionPairError(gambler['display_name'], opponent['display_name'], 'score')

            await ctx.channel.send(f"{gambler['display_name']} {gambler_score} - {opponent_score} {opponent['display_name']}")

            
    @commands.command(aliases=['t'])
    async def transfers(
        self, 
        ctx: Context, 
        gambler_name: Optional[str] = None, 
        opponent_name: Optional[str] = None
    ) -> None:
        '''Shows the accumulative amount of transfers'''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()
            
            if gambler_name == 'all' and opponent_name is None:
                content = ""
                for member in data['members'].values():
                    if ctx.guild.get_member(member['id']) is not None:
                        if member['transfers'] < 0:
                            content += f"{member['display_name']} received {-member['transfers']} coins\n"
                        else:
                            content += f"{member['display_name']} donated {member['transfers']} coins\n"
                await ctx.channel.send(content)
                return

            gambler = None
            if gambler_name is None:
                gambler = data['members'][str(ctx.author.id)]
            else:
                for member in data['members'].values():
                    if gambler_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        gambler = member

            if gambler is None:
                raise InvalidNameError()
        

            if opponent_name is None:
                if gambler['transfers'] < 0:
                    await ctx.channel.send(f"{gambler['display_name']} received a total of {-gambler['transfers']} coins")
                else:
                    await ctx.channel.send(f"{gambler['display_name']} donated a total of {gambler['transfers']} coins")
                return


            elif opponent_name == 'all':
                if len(gambler['transfers_per_mem']) == 0:
                    raise TransactionPairError(gambler['display_name'], 'other members', 'transfers')

                content = f"{gambler['display_name']}:\n"
                for other_id in gambler['transfers_per_mem']:
                    other = data['members'][other_id]
                    amount = gambler['transfers_per_mem'][other_id]
                    if amount >= 0:
                        content += f"donated {amount} to {other['display_name']}"
                    elif amount < 0:
                        content += f"received {-amount} from {other['display_name']}"
                await ctx.channel.send(content)
                return

            else:
                opponent = None
                for member in data['members'].values():
                    if opponent_name == member['display_name'] and ctx.guild.get_member(member['id']) is not None:
                        opponent = member
                        break

                if opponent is None:
                    raise InvalidNameError()

            try:
                amount = gambler['transfers_per_mem'][str(opponent['id'])]
            except KeyError:
                raise TransactionPairError(gambler['display_name'], opponent['display_name'], 'transfers')

            if amount >= 0:
                content = f"{gambler['display_name']} donated {amount} to {opponent['display_name']}"
            elif amount < 0:
                content = f"{gambler['display_name']} received {-amount} from {opponent['display_name']}"
            await ctx.channel.send(content)
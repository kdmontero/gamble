import json, os, asyncio
from collections import OrderedDict
from random import randint, choice

import discord # pip install discord
from discord.ext import commands

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD, PATH
from events import locks
from events import BotEvents
from errors import (
    NotEnoughCoinsError, 
    InvalidAmountError, 
    InvalidNameError,
    RewardError,
    TransactionPairError,
    DataNotFound,
)


class BotActionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def ping(self, ctx):
        await ctx.channel.send("pong")


    @commands.command()
    async def refresh(self, ctx):

        '''Same function call for on_guild_join'''
        self.bot.dispatch('guild_join', ctx.guild)
        await ctx.channel.send("Data refreshed!")


    @commands.command()
    async def gamble(self, ctx, amount, opponent_name=None):
        '''
        Gamble certain amount of coins and have a chance to lose or double it
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


    @commands.command()
    async def yolo(self, ctx):
        '''Same command as gamble all'''
        async with locks[ctx.guild.id]:

            try:
                with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
            except FileNotFoundError:
                raise DataNotFound()
            
            gambler = data['members'][str(ctx.author.id)]
            coins = gambler['coins']
            
            if coins == 0:
                raise NotEnoughCoinsError(ctx.author.display_name, 0)

            result = choice(['win', 'loss'])
            if result == 'win':
                gambler['coins'] *= 2
                gambler['wins'] += 1
                await ctx.channel.send(f"Noice! {ctx.author.display_name} won {coins} coins! You now have {gambler['coins']} coins")
            elif result == 'loss':
                gambler['coins'] = 0
                gambler['losses'] += 1
                await ctx.channel.send(f"Sorry, {ctx.author.display_name} lost {coins} coins. Only {gambler['coins']} coins left")

            with open(f"{PATH}{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command()
    async def claim(self, ctx):
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
            
            if not gambler['has_claimed']:
                raise RewardError('time_left')

            rewards = randint(MIN_REWARD, MAX_REWARD)
            gambler['coins'] += rewards
            gambler['has_claimed'] = True
            await ctx.channel.send(f"{gambler['display_name']} claimed {rewards} coins! You now have {gambler['coins']} coins")
            
            with open(f"{PATH}{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)
    

    @commands.command()
    async def send(self, ctx, amount, receiver_name):
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



class BotDisplayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def wallet(self, ctx, gambler_name=None):
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


    @commands.command()
    async def score(self, ctx, gambler_name=None, opponent_name=None):
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

            
    @commands.command()
    async def transfers(self, ctx, gambler_name=None, opponent_name=None):
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

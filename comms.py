import json, os, asyncio
from collections import OrderedDict
from random import randint, choice

import discord # pip install discord
from discord.ext import commands

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD, PATH
from events import locks
from events import BotEvents


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
    async def gamble(self, ctx, amount):
        '''
        Gamble certain amount of coins and have a chance to lose or double it
        '''
        async with locks[ctx.guild.id]:

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            gambler = data['members'][str(ctx.author.id)]
            coins = gambler['coins']
            
            result = choice(['win', 'loss'])
            
            if amount == 'all':
                bet = coins
            else:
                bet = int(amount)

            if bet > coins:
                await ctx.channel.send(f"Not enough coins... {ctx.author.display_name} only has {coins} coins")
                return
            elif bet <= 0:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a positive value")
                return

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

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            gambler = data['members'][str(ctx.author.id)]
            coins = gambler['coins']
            
            if coins == 0:
                await ctx.channel.send(f"{ctx.author.display_name} cannot YOLO with 0 coins left")
                return

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

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            gambler = data['members'][str(ctx.author.id)]
            
            if not gambler['has_claimed']:
                await ctx.channel.send(f"{gambler['display_name']} already claimed the reward")
                return

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
            amount = int(amount)
            if amount < 1:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a positive value")
                return

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            sender = data['members'][str(ctx.author.id)]

            if sender['coins'] < amount:
                await ctx.channel.send(f"Not enough coins... {ctx.author.display_name} only has {sender['coins']} coins")
                return

            receiver = None
            for member in data['members'].values():
                if receiver_name == member['display_name']:
                    receiver = member
                    break
            
            if sender == receiver or receiver is None:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a valid recipient")
                return
            
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
    async def wallet(self, ctx, gambler_name = None):
        '''Shows the current amount of coins'''
        async with locks[ctx.guild.id]:

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members'].values():
                    content += f"{member['display_name']}: {member['coins']} coins\n"
                await ctx.channel.send(content)

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members'].values():
                    if gambler_name == member['display_name']:
                        coins = member['coins']
                        await ctx.channel.send(f"{gambler_name}: {coins} coins")
                        return

                await ctx.channel.send(f"{ctx.author.display_name}, please enter a valid name")


    @commands.command()
    async def score(self, ctx, gambler_name = None):
        '''Shows the win-loss score'''
        async with locks[ctx.guild.id]:

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members'].values():
                    content += f"{member['display_name']}: {member['wins']} W - {member['losses']} L\n"
                await ctx.channel.send(content)

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members'].values():
                    if gambler_name == member['display_name']:
                        wins = member['wins']
                        losses = member['losses']
                        await ctx.channel.send(f"{gambler_name}: {wins} W - {losses} L")
                        return

            await ctx.channel.send(f"{ctx.author.display_name}, please enter a valid name")


    @commands.command()
    async def transfers(self, ctx, gambler_name = None):
        '''Shows the accumulative amount of transfers'''
        async with locks[ctx.guild.id]:

            with open(f"{PATH}{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members'].values():
                    if member['transfers'] < 0:
                        content += f"{member['display_name']} received {-member['transfers']} coins\n"
                    else:
                        content += f"{member['display_name']} donated {member['transfers']} coins\n"
                await ctx.channel.send(content)
                return

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members'].values():
                    if gambler_name == member['display_name']:
                        if member['transfers'] < 0:
                            await ctx.channel.send(f"{member['display_name']} received {-member['transfers']} coins")
                        else:
                            await ctx.channel.send(f"{member['display_name']} donated {member['transfers']} coins")
                        return

            await ctx.channel.send(f"{ctx.author.display_name}, please enter a valid name")

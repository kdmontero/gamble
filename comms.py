import json, os, asyncio
from collections import OrderedDict
from random import randint, choice

import discord # pip install discord
from discord.ext import commands

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD, BET_TIMEOUT
from events import locks


class BotActionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def ping(self, ctx):
        await ctx.channel.send("pong")


    @commands.command()
    async def refresh(self, ctx):
        '''Same function call for on_guild_join'''
        if locks.get(ctx.guild.id) and os.path.isfile(f'database/{ctx.guild.id}.json'):
            async with locks.get(ctx.guild.id):
                with open(f"database/{ctx.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
                    data['guild_name'] = ctx.guild.name
                    current_ids = {member['id'] for member in data['members']}
                    for member in [member for member in ctx.guild.members if member.bot == False]:
                        if member.id not in current_ids:
                            member_data = OrderedDict()
                            member_data['id'] = member.id
                            member_data['display_name'] = member.display_name
                            member_data['coins'] = INITIAL_COINS
                            member_data['wins'] = 0
                            member_data['losses'] = 0
                            member_data['transfer'] = 0
                            member_data['claim'] = True
                            data['members'].append(member_data)            
                        else:
                            for person in data['members']:
                                if person['id'] == member.id:
                                    person['display_name'] = member.display_name
                        
                with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                    json.dump(data, score_file, indent=4)

        else:
            locks[ctx.guild.id] = asyncio.Lock()
            data = OrderedDict()
            data['guild_id'] = ctx.guild.id
            data['guild_name'] = ctx.guild.name
            data['members'] = []
            for member in [member for member in ctx.guild.members if member.bot == False]:
                member_data = OrderedDict()
                member_data['id'] = member.id
                member_data['display_name'] = member.display_name
                member_data['coins'] = INITIAL_COINS
                member_data['wins'] = 0
                member_data['losses'] = 0
                member_data['transfer'] = 0
                member_data['claim'] = True
                data['members'].append(member_data)

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)

        await ctx.channel.send("Data refreshed!")


    @commands.command()
    async def gamble(self, ctx, amount):
        '''Gamble certain amount of coins and have a chance to lose or double it'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            for member in data['members']:
                if ctx.author.id == member['id']:
                    gambler = member
                    coins = member['coins']
            
            result = choice(['win', 'loss'])
            
            if amount == 'all':
                chips = coins
            else:
                chips = int(amount)

            if chips > coins:
                await ctx.channel.send(f"Not enough coins... {ctx.author.display_name} only has {coins} coins")
            elif chips <= 0:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a positive value")
            else:
                if result == 'win':
                    gambler['coins'] += chips
                    await ctx.channel.send(f"Noice! {ctx.author.display_name} won {chips} coins! You now have {gambler['coins']} coins")
                elif result == 'loss':
                    gambler['coins'] -= chips
                    await ctx.channel.send(f"Sorry, {ctx.author.display_name} lost {chips} coins. Only {gambler['coins']} coins left")

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command()
    async def yolo(self, ctx):
        '''Same as command gamble all'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            for member in data['members']:
                if ctx.author.id == member['id']:
                    gambler = member
                    coins = member['coins']
            
            if coins == 0:
                await ctx.channel.send(f"{ctx.author.display_name} cannot YOLO with 0 coins left")
                return

            result = choice(['win', 'loss'])
            if result == 'win':
                gambler['coins'] *= 2
                await ctx.channel.send(f"Noice! {ctx.author.display_name} won {coins} coins! You now have {gambler['coins']} coins")
            elif result == 'loss':
                gambler['coins'] = 0
                await ctx.channel.send(f"Sorry, {ctx.author.display_name} lost {coins} coins. Only {gambler['coins']} coins left")

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command()
    async def claim(self, ctx):
        '''Claim a random amount of rewards (between MIN_REWARD and MAX_REWARD)'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            for member in data['members']:
                if ctx.author.id == member['id']:
                    gambler = member
            
            if not gambler['claim']:
                await ctx.channel.send(f"{gambler['display_name']} already claimed the reward")
                return

            rewards = randint(MIN_REWARD, MAX_REWARD)
            gambler['coins'] += rewards
            await ctx.channel.send(f"{gambler['display_name']} won {rewards} coins! You now have {gambler['coins']} coins")
            
            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)
    

    @commands.command()
    async def transfer(self, ctx, receiver, amount):
        '''Transfer coins to other user'''
        async with locks.get(ctx.guild.id):
            amount = int(amount)
            if amount < 1:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a positive value")
                return

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            recipient = None
            for member in data['members']:
                if ctx.author.display_name == member['display_name']:
                    gambler = member
                if receiver == member['display_name']:
                    recipient = member
            
            if gambler == recipient:
                return
            
            if gambler['coins'] < amount:
                await ctx.channel.send(f"Not enough coins... {ctx.author.display_name} only has {gambler['coins']} coins")
                return
            else:
                gambler['coins'] -= amount
                gambler['transfer'] += amount
                recipient['coins'] += amount
                recipient['transfer'] -= amount
                await ctx.channel.send(f"{gambler['display_name']} transferred {amount} coins to {recipient['display_name']}")

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


class BotDisplayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def wallet(self, ctx, gambler_name = None):
        '''Shows the current amount of coins'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members']:
                    content += f"{member['display_name']}: {member['coins']} coins\n"
                await ctx.channel.send(content)
                return

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members']:
                    if gambler_name == member['display_name']:
                        coins = member['coins']
                        await ctx.channel.send(f"{gambler_name}: {coins} coins")
                        return


    @commands.command()
    async def score(self, ctx, gambler_name = None):
        '''Shows the win-loss score'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members']:
                    content += f"{member['display_name']}: {member['wins']} W - {member['losses']} L\n"
                await ctx.channel.send(content)
                return

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members']:
                    if gambler_name == member['display_name']:
                        wins = member['wins']
                        losses = member['losses']
                        await ctx.channel.send(f"{gambler_name}: {wins} W - {losses} L")
                        return


    @commands.command()
    async def given(self, ctx, gambler_name = None):
        '''Shows the accumulative amount of transfers'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if gambler_name == 'all':
                content = ""
                for member in data['members']:
                    if member['transfer'] < 0:
                        content += f"{member['display_name']} borrowed {-member['transfer']} coins\n"
                    else:
                        content += f"{member['display_name']} donated {member['transfer']} coins\n"
                await ctx.channel.send(content)
                return

            else:
                if gambler_name == None:
                    gambler_name = ctx.author.display_name
                
                for member in data['members']:
                    if gambler_name == member['display_name']:
                        if member['transfer'] < 0:
                            await ctx.channel.send(f"{member['display_name']} borrowed {-member['transfer']} coins")
                        else:
                            await ctx.channel.send(f"{member['display_name']} donated {member['transfer']} coins")
                        return
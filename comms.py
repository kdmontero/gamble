import json, os, asyncio
from collections import OrderedDict
from random import randint, choice

import discord # pip install discord
from discord.ext import commands

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD
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

        # bot.dispatch('guild_join', ctx.guild)
        # return

        if (
            ctx.guild.id not in locks or 
            not os.path.isfile(f'database/{ctx.guild.id}.json')
        ):
            locks[ctx.guild.id] = asyncio.Lock()
            data = OrderedDict()
            data['guild_id'] = ctx.guild.id
            data['guild_name'] = ctx.guild.name
            data['members'] = {}
            for member in filter(lambda x: x.bot == False, ctx.guild.members):
                BotEvents.initialize_member(data, member, INITIAL_COINS)

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)

            await ctx.channel.send("Data created!")
            return

        async with locks.get(ctx.guild.id):
            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            data['guild_name'] = ctx.guild.name
            for member in filter(lambda x: x.bot == False, ctx.guild.members):
                if str(member.id) not in data['members']:
                    BotEvents.initialize_member(data, member, INITIAL_COINS)
                    continue

                data['members'][str(member.id)]['display_name'] = \
                    member.display_name
                    
            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)

        await ctx.channel.send("Data refreshed!")


    @commands.command()
    async def gamble(self, ctx, amount):
        '''
        Gamble certain amount of coins and have a chance to lose or double it
        '''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if str(ctx.author.id) not in data['members']:
                await ctx.channel.send(f"You have no data yet, try {COMMAND_PREFIX}refresh")
                return


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

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command()
    async def yolo(self, ctx):
        '''Same command as gamble all'''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
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

            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.command()
    async def claim(self, ctx):
        '''
        Claim a random amount of rewards (between MIN_REWARD and MAX_REWARD)
        '''
        async with locks.get(ctx.guild.id):

            with open(f"database/{ctx.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            gambler = data['members'][str(ctx.author.id)]
            
            if not gambler['has_claimed']:
                await ctx.channel.send(f"{gambler['display_name']} already claimed the reward")
                return

            rewards = randint(MIN_REWARD, MAX_REWARD)
            gambler['coins'] += rewards
            gambler['has_claimed'] = True
            await ctx.channel.send(f"{gambler['display_name']} claimed {rewards} coins! You now have {gambler['coins']} coins")
            
            with open(f"database/{ctx.guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)
    

    @commands.command()
    async def send(self, ctx, receiver_name, amount):
        '''Send coins to other user'''
        async with locks.get(ctx.guild.id):
            amount = int(amount)
            if amount < 1:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a positive value")
                return

            with open(f"database/{ctx.guild.id}.json") as score_file:
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
            
            if sender == receiver or receiver == None:
                await ctx.channel.send(f"{ctx.author.display_name}, please enter a valid recipient")
                return
            
            sender['coins'] -= amount
            sender['transfers'] += amount
            receiver['coins'] += amount
            receiver['transfers'] -= amount
            
            if str(receiver.id) in sender['transfers_per_mem']:
                sender['transfers_per_mem'][str(receiver.id)] += amount
            else:
                sender['transfers_per_mem'][str(receiver.id)] = amount

            if str(sender.id) in receiver['transfers_per_mem']:
                receiver['transfers_per_mem'][str(sender.id)] -= amount
            else:
                receiver['transfers_per_mem'][str(sender.id)] = -amount

            await ctx.channel.send(f"{sender['display_name']} transferred {amount} coins to {receiver['display_name']}")

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

import json
# import os
from collections import OrderedDict
from random import randint, choice

import discord # pip install discord
from discord.ext import commands
# from dotenv import load_dotenv # pip install python-dotenv

from const import INITIAL_COINS, MIN_REWARD, MAX_REWARD, BET_TIMEOUT
# import comm
from private import TOKEN

# load_dotenv()
# DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents().all()
command_prefix = "$"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)


# --------------------------- EVENTS --------------------------- #

@bot.event
async def on_ready():
    '''Prompt that bot is ready'''
    print("Let's test your luck!")


@bot.event
async def on_guild_join(guild):
    '''
    Bot will do the following:
    1. Create a score_file in json for the specific guild indicating
    the guild id, guild name, and all non-bot members with initial data.
    2. If a score_file already exists for the guild, it will check changes 
    (guild name was changed, new members were not in the score
    file) and edit accordingly
    '''
    try:
        with open(f"database/{guild.id}.json") as score_file:
            data = json.load(score_file, object_pairs_hook=OrderedDict)
            data['guild_name'] = guild.name
            current_ids = {member['id'] for member in data['members']}
            for member in [member for member in guild.members if member.bot == False]:
                if member.id not in current_ids:
                    member_data = OrderedDict()
                    member_data['id'] = member.id
                    member_data['display_name'] = member.display_name
                    member_data['coins'] = INITIAL_COINS
                    member_data['wins'] = 0
                    member_data['losses'] = 0
                    member_data['donation'] = 0
                    member_data['claim'] = True
                    data['members'].append(member_data)            
                else:
                    for person in data['members']:
                        if person['id'] == member.id:
                            person['display_name'] = member.display_name

    except FileNotFoundError:
        data = OrderedDict()
        data['guild_id'] = guild.id
        data['guild_name'] = guild.name
        data['members'] = []
        for member in [member for member in guild.members if member.bot == False]:
            member_data = OrderedDict()
            member_data['id'] = member.id
            member_data['display_name'] = member.display_name
            member_data['coins'] = INITIAL_COINS
            member_data['wins'] = 0
            member_data['losses'] = 0
            member_data['donation'] = 0
            member_data['claim'] = True
            data['members'].append(member_data)

    with open(f"database/{guild.id}.json", "w") as score_file:
        json.dump(data, score_file, indent=4)


@bot.event
async def on_guild_update(before, after): # before and after are guild classes
    '''Changes the guild name''' 
    if before.name != after.name:
        with open(f"database/{before.id}.json") as score_file:
            data = json.load(score_file, object_pairs_hook=OrderedDict)
        data['guild_name'] = after.name
        with open(f"database/{before.id}.json", 'w') as score_file:
            json.dump(data, score_file, indent=4)


@bot.event
async def on_member_join(new_member):
    '''Adds the new_member into the score_file'''
    with open(f"database/{new_member.guild.id}.json") as score_file:
        data = json.load(score_file, object_pairs_hook=OrderedDict)
    
    for member in data['members']:
        if member['id'] == new_member.id:
            member['display_name'] = new_member.display_name
            break
    else:
        new_member_data = OrderedDict()
        new_member_data['id'] = new_member.id
        new_member_data['display_name'] = new_member.display_name
        new_member_data['coins'] = INITIAL_COINS
        new_member_data['wins'] = 0
        new_member_data['losses'] = 0
        new_member_data['donation'] = 0
        new_member_data['claim'] = True
        data['members'].append(new_member_data)

    with open(f"database/{new_member.guild.id}.json", 'w') as score_file:
        json.dump(data, score_file, indent=4)


@bot.event
async def on_member_update(before, after): # before, after are member class
    '''Changes the member name'''
    if before.display_name != after.display_name:
        with open(f"database/{before.guild.id}.json") as score_file:
            data = json.load(score_file, object_pairs_hook=OrderedDict)

        for member in data['members']:
            if member['id'] == before.id:
                member['display_name'] = after.display_name

        with open(f"database/{before.guild.id}.json", 'w') as score_file:
            json.dump(data, score_file, indent=4)

# coins = 500
# wins = 2
# losses = 3
# claim = True

# @bot.event
# async def on_message(message):
#     if message.author == bot.user:
#         return

#     if message.content == f'{command_prefix}hello':
#         await message.channel.send(f'Hello {message.author.name}!')
#         for member in message.guild.members:
#             print(member.name)
#             print(member.nick)
#             print(member.display_name)
#         if claim:
#             await message.channel.send(f"You won {coins}")


# --------------------------- COMMANDS --------------------------- #

@bot.command()
async def ping(ctx):
	await ctx.channel.send("pong")


@bot.command()
async def refresh(ctx):
    '''Same function call for on_guild_join'''
    try:
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
                    member_data['donation'] = 0
                    member_data['claim'] = True
                    data['members'].append(member_data)            
                else:
                    for person in data['members']:
                        if person['id'] == member.id:
                            person['display_name'] = member.display_name

    except FileNotFoundError:
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
            member_data['donation'] = 0
            member_data['claim'] = True
            data['members'].append(member_data)

    with open(f"database/{ctx.guild.id}.json", "w") as score_file:
        json.dump(data, score_file, indent=4)

    await ctx.channel.send("Data refreshed!")


@bot.command()
async def gamble(ctx, amount):
    '''Gamble certain amount of coins and have a chance to lose or double it'''

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
        await ctx.channel.send(f"Not enough coins... {ctx.author.display_name} only has {coins} coins!")
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


@bot.command()
async def wallet(ctx, gambler_name = None):
    '''Shows the current amount of coins'''

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


@bot.command()
async def claim(ctx):
    '''Claim a random amount of rewards (between MIN_REWARD and MAX_REWARD)'''

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


# --------------------------- COMMANDS --------------------------- #


if __name__ == "__main__":
    bot.run(TOKEN)
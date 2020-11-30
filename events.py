import json, os, asyncio
from collections import OrderedDict

import discord
from discord.ext import commands

from const import INITIAL_COINS


locks = {} # dict for asyncio.Lock() for each score_file per server/guild

class BotStartEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        '''
        Prompt that bot is ready and creates a lock object for each
        database file
        '''
        directory = os.fsencode('database/')
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith('.json'):
                locks[int(filename.rstrip('.json'))] = asyncio.Lock()
        print("Let's test your luck!")



class BotEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        '''
        Bot will do the following:
        1. Create a score_file in json for the specific guild indicating
        the guild id, guild name, and all non-bot members with initial data.
        2. If a score_file already exists for the guild, it will check changes 
        (guild name was changed, new members were not in the score
        file) and edit accordingly
        '''
        if locks.get(guild.id):
            async with locks.get(guild.id):
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
                            member_data['transfer'] = 0
                            member_data['claim'] = True
                            data['members'].append(member_data)            
                        else:
                            for person in data['members']:
                                if person['id'] == member.id:
                                    person['display_name'] = member.display_name
                        
                with open(f"database/{guild.id}.json", "w") as score_file:
                    json.dump(data, score_file, indent=4)

        else:
            locks[guild.id] = asyncio.Lock()
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
                member_data['transfer'] = 0
                member_data['claim'] = True
                data['members'].append(member_data)

            with open(f"database/{guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)


    @commands.Cog.listener()
    async def on_guild_update(self, before, after): # before and after are guild classes
        '''Changes the guild name''' 
        async with locks.get(before.id):
            if before.name != after.name:
                with open(f"database/{before.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
                data['guild_name'] = after.name
                with open(f"database/{before.id}.json", 'w') as score_file:
                    json.dump(data, score_file, indent=4)


    @commands.Cog.listener()
    async def on_member_join(self, new_member):
        '''Adds the new_member into the score_file'''
        async with locks.get(new_member.guild.id):
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
                new_member_data['transfer'] = 0
                new_member_data['claim'] = True
                data['members'].append(new_member_data)

            with open(f"database/{new_member.guild.id}.json", 'w') as score_file:
                json.dump(data, score_file, indent=4)


    @commands.Cog.listener()
    async def on_member_update(self, before, after): # before, after are member class
        '''Changes the member name'''
        async with locks.get(before.guild.id):
            if before.display_name != after.display_name:
                with open(f"database/{before.guild.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)

                for member in data['members']:
                    if member['id'] == before.id:
                        member['display_name'] = after.display_name

                with open(f"database/{before.guild.id}.json", 'w') as score_file:
                    json.dump(data, score_file, indent=4)
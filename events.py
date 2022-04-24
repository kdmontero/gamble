import json, os, asyncio
from collections import OrderedDict

import discord
from discord.ext import commands

from const import INITIAL_COINS, PATH

Guild = discord.guild.Guild
Member = discord.member.Member
Data = OrderedDict # json data


locks = {} # dict for asyncio.Lock() for each score_file per server/guild

class BotStartEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        '''
        Prompt that bot is ready and creates a lock object for each
        guilds it listens to.
        '''
        for guild in self.bot.guilds:
            locks[guild.id] = asyncio.Lock()
        print("Let's test your luck!")



class BotEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    def initialize_member(
        data: OrderedDict, 
        member: Member, 
        INITIAL_COINS: int
    ) -> None:

        '''set the initial data for a non-existing member'''
        member_data = OrderedDict()
        member_data['id'] = member.id
        member_data['display_name'] = member.display_name
        member_data['coins'] = INITIAL_COINS
        member_data['wins'] = 0
        member_data['losses'] = 0
        member_data['transfers'] = 0
        member_data['has_claimed'] = True
        member_data['wins_per_mem'] = {}
        member_data['losses_per_mem'] = {}
        member_data['transfers_per_mem'] = {}
        data['members'][str(member.id)] = member_data


    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        '''
        Bot will do the following:
        1. Create a score_file in json for the specific guild indicating
        the guild id, guild name, and all non-bot members with initial data.
        2. If a score_file already exists for the guild, it will check changes 
        (guild name, or any display name were changed, new members were not in
        the score file) and edit accordingly.
        '''

        locks[guild.id] = asyncio.Lock()
        async with locks[guild.id]:

            # create json file for new server
            if not os.path.isfile(f'{PATH}{guild.id}.json'):
                data = OrderedDict()
                data['guild_id'] = guild.id
                data['guild_name'] = guild.name
                data['members'] = {}
                for member in filter(lambda x: x.bot == False, guild.members):
                    self.initialize_member(data, member, INITIAL_COINS) 

                with open(f"{PATH}{guild.id}.json", "w") as score_file:
                    json.dump(data, score_file, indent=4)
                return


            # load json file if it is already existing (bot has joined before)
            with open(f"{PATH}{guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            data['guild_name'] = guild.name
            for member in filter(lambda x: x.bot == False, guild.members):

                # add initial data for new members
                if str(member.id) not in data['members']:
                    self.initialize_member(data, member, INITIAL_COINS) 
                    continue

                # just update the display name for existing member
                data['members'][str(member.id)]['display_name'] = \
                    member.display_name

            with open(f"{PATH}{guild.id}.json", "w") as score_file:
                json.dump(data, score_file, indent=4)



    @commands.Cog.listener()
    async def on_guild_update(self, before: Guild, after: Guild) -> None:

        '''Changes the guild name''' 
        async with locks[guild.id]:
            if before.name != after.name:
                with open(f"{PATH}{before.id}.json") as score_file:
                    data = json.load(score_file, object_pairs_hook=OrderedDict)
                data['guild_name'] = after.name
                with open(f"{PATH}{before.id}.json", 'w') as score_file:
                    json.dump(data, score_file, indent=4)


    @commands.Cog.listener()
    async def on_member_join(self, new_member: Member) -> None:

        '''Adds the new_member into the score_file'''
        async with locks[new_member.guild.id]:
            with open(f"{PATH}{new_member.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)
            
            if str(new_member.id) in data['members']:
                data['members'][str(new_member.id)]['display_name'] = \
                    new_member.display_name

            else:
                self.initialize_member(data, new_member, INITIAL_COINS)

            with open(f"{PATH}{new_member.guild.id}.json",'w') as score_file:
                json.dump(data, score_file, indent=4)


    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:

        '''Changes the member name'''
        async with locks[before.guild.id]:
            if before.display_name == after.display_name:
                return

            with open(f"{PATH}{before.guild.id}.json") as score_file:
                data = json.load(score_file, object_pairs_hook=OrderedDict)

            data['members'][str(before.id)]['display_name'] = after.display_name

            with open(f"{PATH}{before.guild.id}.json",'w') as score_file:
                json.dump(data, score_file, indent=4)

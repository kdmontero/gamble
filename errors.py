import discord
from discord.ext.commands.errors import (UserInputError, CommandError)


class NotEnoughCoinsError(UserInputError):
    '''Error raised when the bet/transfers is too large'''

    def __init__(self, name, coins):
        self.coins = coins
        self.name = name
        self.message = f'Not enough coins. {name} only has {coins} coins'


class InvalidAmountError(UserInputError):
    '''Error raised when the bet/transfers is not a positive integer'''

    def __init__(self):
        self.message = 'Please enter a valid amount'


class InvalidNameError(UserInputError):
    '''Error raised when the member name is not found'''

    def __init__(self):
        self.message = 'Please enter a valid name'


class RewardError(CommandError):
    '''
    Error raised when the reward is already claimed (timer is still in cooldown)
    '''

    def __init__(self, time_left):
        self.time_left = time_left
        self.message = f'Reward already claimed. Please wait {self.time_left} minutes'


class TransactionPairError(CommandError):
    '''
    Error raised when the given pair of members in "transfers" or "score"
    command has not yet transacted, or the same member name is provided.
    '''

    def __init__(self, member1, member2, transaction):
        self.member1 = member1
        self.member2 = member2
        self.transaction = transaction
        self.message = f'{member1} has no {transaction} yet with {member2}'


class DataNotFound(CommandError):
    '''Error raised when a member or guild data is not found'''

    def __init__(self):
        self.message = 'Data not found. Try $refresh'

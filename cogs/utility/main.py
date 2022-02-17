
from discord.ext import commands
from utils.dpy import setuphelper
import discord
import asyncio
from utils.misc import aobject


@setuphelper.attach_task_manager
@setuphelper.helpargs(name="Utility", desc="Utility commands for setting up basic usability")
class Greetings(aobject, commands.Cog):
    async def __init__(self, client, main, **kwargs):
        self.client = client
        self.main = main

    # # first arg is global order, second arg is local order
    # # global order is a INDEPENDENT event line off the local order
    # @setuphelper.global_start_func(1, 1) 
    # async def func1(self):
    #     print("here 1")
        
    # @setuphelper.global_start_func(3, 2) # will be executed 3rd GLOBALLY but second LOCALLY, so there might be another global function inserted between 1 and 2nd
    # async def func2(self):
    #     print("here 3")
        
    # same concept with close funcs
    # @setuphelper.global_close_func(2)
    # async def close1(self):
    #     print("closing 1")
    

COG = Greetings
GLOBALS = globals()
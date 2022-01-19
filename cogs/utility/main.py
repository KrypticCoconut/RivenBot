
from discord.ext import commands
from utils.dpy import setuphelper
import discord
import asyncio
from utils.misc import aobject

@setuphelper.attach_task_manager
@setuphelper.helpargs(name="Utility", desc="Utility commands")
class Greetings(aobject, commands.Cog):
    async def __init__(self, client, main, **kwargs):
        self.client = client
        self.main = main
    
    # @setuphelper.init_func(1) # 1 is the priority, lesser priority = faster starting
    # async def start(self):
    #     # will be ran first
    #     await asyncio.sleep(5)
    #     # no command can be executed before the start function starts, assuming it has a blocker atached to it

    # @setuphelper.init_func(2)
    # # will be ran 2nd
    # async def start2(self):
    #     print("second")

        
COG = Greetings
GLOBALS = globals()
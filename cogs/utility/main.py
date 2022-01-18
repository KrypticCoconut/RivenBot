
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
    
    @setuphelper.init_func(1) # 1 is the priority, greater priority = faster starting
    async def start(self):
        print("first")
        # print("start")
        # await asyncio.sleep(5)
        # print("end")
        # no command can be executed before the start function starts, assuming it has a blocker atached to it
        return
    
        
    @setuphelper.init_func(2)
    async def start2(self):
        print("second")
        return

        
COG = Greetings
GLOBALS = globals()
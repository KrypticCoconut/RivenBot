
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
    
    @setuphelper.init_func
    async def start():
        # print("start")
        # await asyncio.sleep(5)
        # print("end")
        pass
        
COG = Greetings
GLOBALS = globals()
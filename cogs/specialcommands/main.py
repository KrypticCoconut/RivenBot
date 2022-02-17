
from discord.ext import commands
from utils.dpy import setuphelper
import discord
import asyncio
from utils.misc import aobject


@setuphelper.attach_task_manager
@setuphelper.helpargs(name="SpecialCommands", desc="User defined commands")
class SpecialCommands(aobject, commands.Cog):
    async def __init__(self, client, main, **kwargs):
        self.client = client
        self.main = main

COG = SpecialCommands
GLOBALS = globals()
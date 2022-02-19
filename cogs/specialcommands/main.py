
from sys import prefix
from discord.ext import commands
from cogs.utility.help import setup_help
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
        
    @setuphelper.cog_start_func
    async def wrap_on_message(self):
        og = self.main.client.on_message
        
        async def wrapper(*args, **kwargs):
            await og(*args, **kwargs)
            
            ctx = args[0]
            id = ctx.guild.id
            message = ctx.content
            
            found = False
            for prefix in await self.client.command_prefix(self.client, ctx):
                if(message.startswith(prefix)):
                    found = True
                    break
            if(not found):
                return
            
            command = message[len(prefix):].split(" ")[0]
            p_key = "{}_{}".format(id, command)
            row = await customcommands.get_row(p_key)
            if(row):
                await ctx.channel.send(row["text"])
            
                    
            
        self.main.client.on_message = wrapper
            
    @setuphelper.cog_start_func
    async def get_predef_commands(self):
        self.commands = []
        for cog in self.main.cogs.values():
            for command in cog.commands:
                self.commands.append(command.name)

COG = SpecialCommands
GLOBALS = globals()
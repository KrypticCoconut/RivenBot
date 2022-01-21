from pydoc import cli
from discord.ext import commands
from utils.dpy import setuphelper
from discord.ext.commands import has_permissions

@setuphelper.helpargs(name="close", desc="Used to close the bot", hidden=True)
@commands.command()

async def close(self, ctx):
    if(ctx.author.id in self.main.config["admins"]):
        await self.main.close()
        
    
COMMAND = close
GLOBALS = globals()
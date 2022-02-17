
                
                
from discord.ext import commands
from utils.dpy import setuphelper
import discord

usage = """
!help categories <category> -> prints all commands and subcategories in specified category, if provided none the base category is root
!help commands -> prints all commands
!help <command> -> gives help message for command
"""

@setuphelper.helpargs(name="help", desc="help command", usage=usage)
@setuphelper.attach_blocker
@setuphelper.notifier
@commands.command()
async def help(self, ctx):
    await ctx.send(embed=self.tree_embed)

    
COMMAND = help
GLOBALS = globals()
SETUPFUNCS = []
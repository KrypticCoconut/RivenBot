from discord.ext import commands
from utils.dpy import setuphelper
import discord


@setuphelper.helpargs(name="tree", desc="!tree")
@commands.command()
@setuphelper.attach_blocker
@setuphelper.notifier
async def tree(self, ctx):
    await ctx.send(embed=self.tree_embed)

    
COMMAND = tree
GLOBALS = globals()
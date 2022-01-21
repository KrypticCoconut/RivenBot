from hashlib import new
from discord.ext import commands
from utils.dpy import setuphelper
import discord


@setuphelper.helpargs(name="prefix", desc="!prefix")
@setuphelper.attach_blocker
@setuphelper.notifier
@commands.command()
async def prefix(self, ctx, *args):
    if(not len(args) >= 1):
        embed=discord.Embed(title="Please specify a prefix to change to", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    prefix = args[0]
    if(prefix.lower() == "none"):
        prefix = None
    elif(len(prefix) > 4):
        embed=discord.Embed(title="Prefix needs to be lower than 3 characters", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    row = await servers.get_row(primary_key=ctx.guild.id, root="servers", conf={})
    oldprefix = row["prefix"]
    row["prefix"] = prefix
    
    embed=discord.Embed(title="Changed prefix!", description="`{}` => `{}`\nBot will always respond on ping".format(oldprefix, prefix), color=discord.Color.green())
    await ctx.send(embed=embed)

    
COMMAND = prefix
GLOBALS = globals()
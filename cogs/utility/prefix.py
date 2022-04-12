from hashlib import new
from discord.ext import commands
from utils.dpy import setuphelper
import discord
from sqlalchemy.future import select
import time

async def get_perms(self, ctx):
    template = {"users": [], "roles": [], "everyone": False}

    
    table = moderatorroles.table
    stmt = select(table).where(table.server_id == ctx.guild.id)
    rows = await moderatorroles.get_row(stmt)
    
    if(rows): 
        roles = list(map(lambda x: x["role_id"], rows))
        template["roles"].extend(roles)
    template["users"].append(ctx.guild.owner_id)

    return template

@setuphelper.helpargs(name="prefix", desc="used to change prefix, needs moderator or owner access", usage="!prefix <newprefix> // changes pefix to <newprefix>")
@setuphelper.attach_blocker
@setuphelper.notifier
@setuphelper.has_perms(get_perms)
@commands.command()
async def prefix(self, ctx, *args):
    start_time = time.time()

    if(not len(args) >= 1):
        embed=discord.Embed(title="Please specify a prefix to change to", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    prefix = args[0]
    if(prefix.lower() == "none"):
        prefix = None
    elif(len(prefix) > 100):
        embed=discord.Embed(title="Prefix needs to be shorter than 4 characters", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    message = ctx.message
    row = await servers.get_row(primary_key=ctx.guild.id)
    oldprefix = row["prefix"]
    await row.change("prefix", prefix)

    embed=discord.Embed(title="Changed prefix!", description="`{}` => `{}`\nBot will always respond on ping".format(oldprefix, prefix), color=discord.Color.green())
    await ctx.send(embed=embed)
    
    print("--- %s seconds ---" % (time.time() - start_time))







COMMAND = prefix
GLOBALS = globals()
CLASS_ATTRS = []
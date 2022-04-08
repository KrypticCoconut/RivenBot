from hashlib import new
from discord.ext import commands
from utils.dpy import setuphelper
import discord
from sqlalchemy.future import select

usage = """
!log_channel <channel_id> // sets log channel to given channel
!log_channel None // sets log channel to None
"""

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

@setuphelper.helpargs(name="log_channel", desc="used to change logging channel, needs moderator or owner access", usage=usage)
@setuphelper.attach_blocker
@setuphelper.notifier
@setuphelper.has_perms(get_perms)
@commands.command()
async def log_channel(self, ctx, *args):
    if(not len(args) >= 1):
        embed=discord.Embed(title="Please specify a channel or None", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    channel = args[0]

    if(channel.lower() == "none"):
        channel = None
    else:
        if(not channel.startswith("<#") or not channel.endswith(">")):
            embed=discord.Embed(title="Please specify a valid channel", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
            
        channel = channel[2:-1]
        if(channel == ''):
            embed=discord.Embed(title="Please specify a valid channel", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        channel = int(channel)
        
        if(not ctx.guild.get_channel(channel)):
            embed=discord.Embed(title="Please specify a valid channel", color=discord.Color.red())
            await ctx.send(embed=embed)
            return        

        config = await servers.get_row(ctx.guild.id)
        await config.change("log_id", channel)
        embed=discord.Embed(title="Logging channel set to given channel!", color=discord.Color.green())
        await ctx.send(embed=embed)
        return
    

    # message = ctx.message
    # row = await servers.get_row(primary_key=ctx.guild.id, conf={"server_id": message.guild.id})
    # oldprefix = row["prefix"]
    # await row.change("prefix", prefix)

    # embed=discord.Embed(title="Changed prefix!", description="`{}` => `{}`\nBot will always respond on ping".format(oldprefix, prefix), color=discord.Color.green())
    # await ctx.send(embed=embed)




COMMAND = log_channel
GLOBALS = globals()
CLASS_ATTRS = []
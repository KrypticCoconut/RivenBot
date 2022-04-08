from hashlib import new
from re import L
from signal import pthread_kill
from discord.ext import commands
from utils.dpy import setuphelper
import discord
from sqlalchemy.future import select
from discord.utils import get


usage = """
!moderator add <mod_role> // add moderator role
!moderator delete <mod_role> // delete moderator role
!moderator list // lists roles
"""

async def get_perms(self, ctx):
    template = {"users": [], "roles": [], "everyone": False}

    template["users"].append(ctx.guild.owner_id)
    
    return template


@setuphelper.helpargs(name="moderator", desc="used to add or delete moderator roles", usage=usage)
@setuphelper.attach_blocker
@setuphelper.notifier
@setuphelper.has_perms(get_perms)
@commands.command()
async def moderator(self, ctx, *args):
    if(not len(args) >= 1):
        embed=discord.Embed(title="Please specify a mode", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    
    mode = args[0]
    cache = moderatorroles
    
    if(mode.lower() != "list"):
        if(not len(args) >= 2):
            embed=discord.Embed(title="Please specify a role", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        role = args[1]
        if(not role.startswith("<@&") or not role.endswith(">")):
            embed=discord.Embed(title="Please specify a valid role", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
            
        role = role[3:-1]
        if(role == ''):
            embed=discord.Embed(title="Please specify a valid role", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        role = int(role)
        # print(ctx.guild.get_role(role), role, ctx.guild.roles)
        if(not ctx.guild.get_role(role)):
            embed=discord.Embed(title="Please specify a valid role", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        
            
        if(mode.lower() == "add"):
            config = {
                "server_id": ctx.guild.id,
                "role_id": role
            }

            if(await cache.get_row(role)):
                embed=discord.Embed(title="Role is already in moderator roles", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
            
            await cache.add_conf(config, check=False)
            
            embed=discord.Embed(title="Added role in moderator roles!", color=discord.Color.green())
            await ctx.send(embed=embed)
            return
        elif(mode.lower() == "delete"):
            conf = await cache.get_row(role)
            if(conf == None):
                embed=discord.Embed(title="Role is not moderator roles", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
            await cache.del_row(role, prev_conf = conf, check=False)
            embed=discord.Embed(title="Deleted role from moderator roles!", color=discord.Color.green())
            await ctx.send(embed=embed)
            return
    else:
        
        stmt = select(cache.table).where(cache.table.server_id == ctx.guild.id)
        rows = await cache.get_row(stmt)
        
        roles = ""
        if(rows): 
            roles = ', '.join(list(map(lambda x: ctx.guild.get_role(x["role_id"]).name, rows)))
        
        embed=discord.Embed(title="Moderator Roles", color=discord.Color.green(), description = roles)
        await ctx.send(embed=embed)
        return
        
        
    

COMMAND = moderator
GLOBALS = globals()
CLASS_ATTRS = []
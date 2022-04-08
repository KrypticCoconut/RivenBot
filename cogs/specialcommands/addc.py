from linecache import cache
from discord.ext import commands
from sqlalchemy import true
from utils.dpy import setuphelper
import discord
from sqlalchemy.future import select

async def get_perms(self, ctx):
    template = {"users": [], "roles": [], "everyone": False}
    config = {
        "server_id": ctx.guild.id,
        "customcommandssettings": {
            "server_id": ctx.guild.id,
            "everyone_addc": True,
        }
    }
    row = await customcommandssettings.get_row(primary_key=ctx.guild.id, conf=config, root="servers")
    template["everyone"] = row["everyone_addc"]
    
    table = customcommandsroles.table
    stmt = select(table).where(table.addc == True)
    rows = await customcommandsroles.get_row(stmt)
    
    if(rows): 
        roles = list(map(lambda x: x["role_id"], rows))
        # roles_in_server = list(map(lambda x: x.id, ctx.guild.roles))
        # for role in roles:
        #     if(role not in roles_in_server):
        # for role in roles:
        template["roles"].extend(roles)
    template["users"].append(ctx.guild.owner_id)

    return template

@setuphelper.helpargs(name="addc", desc="add command", usage="!addc")
@setuphelper.attach_blocker
@setuphelper.notifier
@setuphelper.has_perms(get_perms)
@commands.command()
async def addc(self, ctx, *args):
    if(len(args) < 2):
        await ctx.send(embed=discord.Embed(title="Please specify the command name and command text", color=discord.Color.red()))
        return
    
    name = args[0]
    text = ' '.join(ctx.message.content.split(" ")[2:])
    pkey = "{}_{}".format(ctx.guild.id, name)
    
    if(name in self.commands):
        await ctx.send(embed=discord.Embed(title="Predifined command with name {} already exists, please use another name".format(name), color=discord.Color.red()))
        return
    if(len(pkey) > 500):
        await ctx.send(embed=discord.Embed(title="Command name must be shorter by {} characters".format(-1 *(500 - len(pkey))), color=discord.Color.red()))
        return
    
    row = await customcommands.get_row(primary_key=pkey) # kind of redundant but im lazy
    if(row):
        await ctx.send(embed=discord.Embed(title="Command '{}' already exists".format(name), color=discord.Color.red()))
        return
    
    config = { # we dont need to start from root since the perm check already does that
        "command_id": pkey,
        "name": name,
        "text": text,
        "creator": ctx.author.id,
        "server_id": ctx.guild.id
    }
    
    result = await customcommands.get_row(primary_key = pkey, conf=config)
    await ctx.send(embed=discord.Embed(title="Successfully added command '{}'!".format(name), color=discord.Color.green()))



COMMAND = addc
GLOBALS = globals()
CLASS_ATTRS = []
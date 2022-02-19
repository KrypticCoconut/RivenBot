from linecache import cache
from discord.ext import commands
from utils.dpy import setuphelper
import discord

@setuphelper.helpargs(name="addc", desc="add command", usage="!addc")
@setuphelper.attach_blocker
@setuphelper.notifier
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

    row = await customcommands.get_row(primary_key=pkey)
    if(row):
        await ctx.send(embed=discord.Embed(title="Command '{}' already exists".format(name), color=discord.Color.red()))
        return
    
    config = {
        "server_id": ctx.guild.id,
        "customcommandssettings": {
            "server_id": ctx.guild.id,
            "everyone_addc": True,
            "customcommands": {
                "command_id": pkey,
                "name": name,
                "text": text,
                "creator": ctx.author.id,
                "server_id": ctx.guild.id
            }
        }
    }

    result = await customcommands.get_row(primary_key = pkey, conf=config, root="servers")
    await ctx.send(embed=discord.Embed(title="Successfully added command '{}'!".format(name), color=discord.Color.green()))



COMMAND = addc
GLOBALS = globals()
CLASS_ATTRS = []
from discord.ext import commands
from utils.dpy import setuphelper
import discord
import sys
import distutils
    
    
@setuphelper.helpargs(name="addc_everyone", shortdesc="Anyone can add a special command", desc = "If set to true, anyone will be able to create a special command, true by default", 
usage="""
!addc_everyone true -> anyone will be able to set special commands
!addc_everyone false -> only people with permissions and the owner will be able to set special commands
""")
@setuphelper.attach_blocker
@setuphelper.notifier
@commands.command()
async def addc_everyone(self, ctx, *args):
    if(not args):
        await self.ctx.channel.send(embed = discord.Embed(title="Please supply true or false", color = discord.Color.red()))
        return
    arg = args[0].lower()
    if(not arg in ["true", "false"]):
        await self.ctx.channel.send(embed = discord.Embed(title="Please supply true or false", color = discord.Color.red()))
        return
    
    if(arg == "false"):
        arg = False
    else:
        arg = True

    config = {
        "server_id": ctx.guild.id,
        "customcommandssettings": {
            "server_id": ctx.guild.id,
            "everyone_addc": arg,
        }
    }
    

    row = await customcommandssettings.get_row(primary_key=ctx.guild.id, conf=config, root="servers")
    await row.change("everyone_addc", arg) # redundant code 50 50
    await ctx.send(embed=discord.Embed(title="Set everyone_addc to {}".format(arg), color = discord.Color.green()))



COMMAND = addc_everyone
GLOBALS = globals()
CLASS_ATTRS = []
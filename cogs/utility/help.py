
                
                
from cgitb import text
import dis
from discord.ext import commands
from sqlalchemy import all_, desc
from urllib3 import Retry
from utils.dpy import setuphelper
import discord

usage = """
!help commands -> prints all commands
!help categories -> prints all categories
!help <category> -> prints all commands and subcategories in specified category
!help <command> -> gives help message for command
"""

# help_commands = {}
# help_categories = {}
# all_commands = None
# all_categories = None

@setuphelper.helpargs(name="help", desc="help command", usage=usage)
@setuphelper.attach_blocker
@setuphelper.notifier
@commands.command()
async def help(self, ctx, *args):
    if(not args):
        await ctx.send(embed=self.all_help)
        return
    arg = args[0].lower()
    
    if(arg == "commands"): 
        await ctx.send(embed=self.all_commands)
        return
    if(arg == "categories"): 
        await ctx.send(embed=self.all_cogs)
        return
    
    if(arg in self.command_help.keys()):
        await ctx.send(embed=self.command_help[arg])
        return
    if(arg in self.cog_help.keys()):
        await ctx.send(embed=self.cog_help[arg])
        return

def iterator(cog, cogs=[], commands=[]):
    for command in cog.commands:
        commands.append(command)
    for child_cog in cog.children:
        cogs.append(child_cog.name)
        _cogs, _commands = iterator(cogs, commands)
        cogs.extend(_cogs)
        _commands.extend(command)
    return cogs, commands

@setuphelper.cog_start_func
async def setup_help(self):
    commands = []
    cogs = []
    for name, cog in self.main.cogs.items():
        cogs.append(cog)
        _cogs, _commands = iterator(cog)
        cogs.extend(_cogs)
        commands.extend(_commands)
    
    all_commands = ""
    for command in commands:
        if(command.hidden):
            continue
        all_commands += "{} - {}\n".format(command.name.capitalize(), command.shortdesc.capitalize())
    all_commands = "```\n{}\n```".format(all_commands).rstrip().lstrip()
    self.all_commands = discord.Embed(title="All Commands", description=all_commands)
    self.all_commands.set_footer(text="Use help <command> for detailed info")

    all_cogs = ""
    for cog in cogs:
        all_cogs += "{} - {}\n".format(cog.name.capitalize(), cog.shortdesc.capitalize())
    all_cogs = "```\n{}\n```".format(all_cogs).rstrip().lstrip()
    self.all_cogs = discord.Embed(title="All Categories", description=all_cogs)
    self.all_cogs.set_footer(text="Use help <category> for detailed info")
    
    self.all_help = discord.Embed(title="All categories and commands", description="```{}```".format(help.usage))
    self.all_help.add_field(name="All Commands", value=all_commands, inline=False)
    self.all_help.add_field(name="All Categories", value=all_cogs, inline=False)
    
    
    self.command_help = {}
    self.cog_help = {}
    
    for command in commands:
        if(command.hidden):
            continue
        name = command.name.capitalize()
        embed = discord.Embed(title=name)
        embed.add_field(name="Description", value="```{}```".format(command.desc), inline=False)
        embed.add_field(name="Usage", value="```{}```".format(command.usage), inline=False)
        self.command_help[command.name.lower()] = embed
        
        
    for cog in cogs:
        if(cog.hidden):
            continue
        name = cog.name.capitalize()
        embed = discord.Embed(title=name)
        embed.add_field(name="Description", value="```{}```".format(cog.desc), inline=False)
        _commands = ""
    
        for command in cog.commands:
            if(command.hidden):
                continue
            _commands += "{} - {}\n".format(command.name.capitalize(), command.shortdesc.capitalize())
        embed.add_field(name="Commands", value="```{}```".format(_commands), inline=False)
        _cogs = ""
        for cog in cog.children:
            if(cog.hidden):
                continue
            _cogs += "{} - {}\n".format(cog.name.capitalize(), cog.shortdesc.capitalize())
        embed.add_field(name="Subcategories", value="```\n{}\n```".format(_cogs), inline=False)
        self.cog_help[cog.name.lower()] = embed
    
COMMAND = help
GLOBALS = globals()
CLASS_ATTRS = [setup_help]
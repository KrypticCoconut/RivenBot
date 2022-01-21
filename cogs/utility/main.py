
from discord.ext import commands
from utils.dpy import setuphelper
import discord
import asyncio
from utils.misc import aobject
import sys
from treelib import Node, Tree
import sys
from io import StringIO


def create_list(cogs, tree, parent=None):
    for cog in cogs:
        tree.create_node(cog.name, cog.name, parent=parent)
        for command in cog.commands:
            if(command.hidden):
                continue
            tree.create_node(command.name, command.name, parent=cog.name)
        create_list(cog.children, tree, parent=cog.name)
    return tree

def get_tree(self):
    starts = []
    for cog in self.main.cogs.values():
        if(cog.hidden):
            continue
        if(cog.parent == None):
            starts.append(cog)
    t = Tree()
    t = create_list(starts, t)
    
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    t.show()
    sys.stdout = old_stdout

    val = mystdout.getvalue()
    return val.rstrip().lstrip()

@setuphelper.attach_task_manager
@setuphelper.helpargs(name="Utility", desc="Utility commands")
class Greetings(aobject, commands.Cog):
    async def __init__(self, client, main, **kwargs):
        self.client = client
        self.main = main
    
    @setuphelper.init_func 
    async def start(self):
        tree = get_tree(self)
        self.tree_embed = embed=discord.Embed(title="Tree view of commands", description="```\n{}\n```".format(tree))


    # @setuphelper.init_func(2)
    # # will be ran 2nd
    # async def start2(self):
    #     print("second")

        
COG = Greetings
GLOBALS = globals()
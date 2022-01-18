from discord.ext import commands
from utils.dpy import setuphelper
import discord
from treelib import Node, Tree
import sys
from io import StringIO

def create_list(cogs, tree, parent=None):
    for cog in cogs:
        tree.create_node(cog.name, cog.name, parent=parent)
        for command in cog.commands:
            tree.create_node(command.name, command.name, parent=cog.name)
        create_list(cog.children, tree, parent=cog.name)
    return tree


@setuphelper.helpargs(name="tree", desc="!tree")
@commands.command()
@setuphelper.attach_blocker
@setuphelper.notifier
async def tree(self, ctx):
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

    # print(mystdout.getvalue())
    
COMMAND = tree
GLOBALS = globals()
from discord.ext import commands
from utils.dpy import setuphelper
import discord
from treelib import Node, Tree
from io import StringIO
import sys

@setuphelper.helpargs(name="tree", desc="tree view of all commands", usage="!tree")
@setuphelper.attach_blocker
@setuphelper.notifier
@commands.command()
async def tree(self, ctx):
    await ctx.send(embed=self.tree_embed)


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

async def setup_tree(self):
    tree = get_tree(self)
    self.tree_embed = embed=discord.Embed(title="Tree view of commands", description="```\n{}\n```".format(tree))
    
COMMAND = tree
GLOBALS = globals()
SETUPFUNCS = [setup_tree]
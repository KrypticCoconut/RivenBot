
import json
import os
import importlib
from pydoc import cli
from sys import prefix

import discord
from discord.ext import commands
import asyncio


from utils.dpy import setup

class Cog(object):
    def __init__(self, cog, globals, commands, instance, parent) -> None:
        super().__init__()
        self.cog = cog
        
        self.name = cog.name
        self.desc = cog.desc
        self.usage = cog.usage
        self.shortdesc = cog.shortdesc
        self.hidden = cog.hidden
        self.parent = parent
        self.children = []
        if(parent):
            parent.children.append(self)
        
        self.globals = globals
        self.commands = commands
        
        cog.commands = commands
        cog.main = self
        
        self.instance = instance
        

    
class Command(object):
    def __init__(self, command, globals) -> None:
        super().__init__()
        self.command = command
        
        
        self.name = command.name
        self.desc = command.desc
        self.usage = command.usage
        self.shortdesc = command.shortdesc
        self.hidden = command.hidden
        
        self.globals = globals

class Main(object):
    def __init__(self, setup_file) -> None:
        super().__init__()
        
        self.cwd = os.getcwd()
        self.pwd = os.path.dirname(os.path.realpath(__file__))
        
        self.load_setup(os.path.join(self.pwd, setup_file))
        
        self.cogs = {}
        self.modules = {}
        
        self.cogs_loaded = False
        self.modules_loaded = False
        
        self.injects = {}
        

        
        
    def load_setup(self, setup_file):
        content = json.load(open(setup_file, "r"))
        self.config = content

    async def load_cog(self, path, parent):
        main = None
        commands = []
        for f in os.listdir(path):
            
            if(f == "main.py"):
                main = os.path.join(path, f)
            elif(f.endswith(".py")):
                commands.append(os.path.join(path, f))
                
        if(not main):
            return False, True, "Unable to find 'main.py' in {}".format_map(path)
        
        spec = importlib.util.spec_from_file_location("main", main)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            cog = module.COG
            cog_globals = module.GLOBALS
        except AttributeError:
            return False, True, "root command variables are not declared in '{}'".format(main)
        

        
        command_objs = []
        for command_p in commands:
            spec = importlib.util.spec_from_file_location("module", command_p)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                command = module.COMMAND
                command_globals = module.GLOBALS
                class_attrs = module.CLASS_ATTRS
            except AttributeError:
                self.primary.debug("Unable to load command '{}' root vars not declared".format(command_p))
                continue
            
            for attr in class_attrs:
                setattr(cog, attr.__name__, attr)
            cog.__cog_commands__.append(command)
            command_obj = Command(command, command_globals)
            command_objs.append(command_obj)
        
        instance = await cog(client = self.client, main = self)
        cog_obj = Cog(cog, cog_globals, command_objs, instance, parent)
        self.cogs[cog.name] = cog_obj
        self.client.add_cog(instance)
        await self.primary.debug("Loaded cog '{}'".format(cog.name))
        return True, False, cog_obj
    
    async def load_cogs(self, cog_dir, parent):
        for folder in os.listdir(cog_dir):
            p = os.path.join(cog_dir, folder)
            if(os.path.isdir(p) and folder != "__pycache__"):
                # print(p)
                ret = await self.load_cog(p, parent)
                if(not ret[0] and ret[1]):
                    self.primary.debug(ret[2])
                if(ret[0]):
                    # print("here")
                    await self.load_cogs(p, ret[2]) # tf this breaks stuff no
                    
        self.cogs_loaded = True
    
    async def load_module(self, path):
        
        spec = importlib.util.spec_from_file_location("module", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try: 
            cls = module.MOD
            name = module.NAME
        except AttributeError:
            return False, True, "Unable to load module '{}', undeclared 'cls' or 'name'".format(path)
        
        if(name in self.modules.keys()):
            return False, False, None
        conf = self.config["modules"].get(name)
        if(not conf):
            return False, True, "No config for module '{}'".format(name)
        for name2, val in conf.items():
            if(val == "%main"):
                conf[name2] =  self
        
        instance = await cls(**conf)
        setattr(self, name, instance)
        self.modules[name] = instance
        await self.primary.debug("Loaded module '{}'".format(name))
        return True, False, [name, instance]
        
    async def load_modules(self, mod_dir):
        mod_dir = os.path.join(self.pwd, mod_dir)
        self.mod_dir = mod_dir
        order = json.load(open(os.path.join(mod_dir, "load_order.json"), "r"))
        self.mod_order = order
        
        for file in order:
            file = file + ".py"
            path = os.path.join(mod_dir, file)
            ret = await self.load_module(path)
            if(not ret[0] and ret[1]): # [loaded?, debug?, debug_err]
                await self.primary.debug(ret[2])
                
                
        self.modules_loaded = True
    
    async def attach_prefix(self):

        async def get_prefix(ctx, message):
            conf = await self.caches["servers"].get_row(message.guild.id, "servers", conf={"server_id": message.guild.id})
            prefix =  commands.when_mentioned(ctx, message) + [conf["prefix"]]
            return prefix
        
        

        self.client.command_prefix = get_prefix
    
    async def close(self):
        await self.setup_helper.call_close_funcs()
        await self.primary.debug("Running Module close functions")
        for module in self.mod_order[::-1]: # call them in reverse order because dependent mods were loaded first so they should be unloaded last
            name = module
            module = self.modules[module]
            f = getattr(module, "closing_func", None)
            if(f):
                await self.primary.debug("Running closing func for module '{}'".format(name))
                await f()
                
        await self.client.close()

                
        
    async def start(self, cog_dir, mod_dir):
        client = commands.Bot(command_prefix=None, help_command=None) # None is temp
        self.client = client
        
        @self.client.event
        async def on_ready():
            await self.primary.debug("Bot started")
        
        self.setup_helper = setup(self) # initialize dpy object for cog loading
        
        self.cog_root = cog_dir
        await self.load_modules(mod_dir)
        await self.load_cogs(os.path.join(self.pwd, cog_dir), None)
        
        await self.attach_prefix()
         
        #shut up im good at coding
        for name, object in self.injects.items():
            for cog in self.cogs.values():
                cog.globals[name] = object
                for command in cog.commands:
                    command.globals[name] = object
        del self.injects
        
        
        try:
            await self.client.start(self.config["token"])
        except:
            await self.close()
        await self.primary.debug("Client Closed")
    
        
    def inject_globals(self, name, object):
        if(not self.cogs_loaded):
            self.injects[name] = object
        else:
            raise Exception("Global inject tried after cogs were loaded")
            

    
    
    def header(self, text):
        l = 100
        if(not (len(text) % 2 == 0)):
            l = l + 1
            
        ret = ""
        ret += "-"*l + "\n"
        div = int((l-len(text))/2)
        ret += "-"*div + text + "-"*div + "\n"
        ret += "-"*l
        return ret
    
        

        
if __name__ == "__main__":
    main = Main("config.json")
    asyncio.run(main.start("cogs", "utils/modules"))


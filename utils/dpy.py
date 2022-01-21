from collections import _OrderedDictValuesView
from curses import wrapper
from typing_extensions import Self
from discord.ext import commands
import asyncio
import discord

class TaskManager(object):
    def __init__(self, cls, main, helper) -> None:
        self.main = main
        self.cog = cls
        self.helper = helper
        
        self.startup_funcs = []
        self.start_funcs_called = False
        
        self.closing_funcs = []
        
        self.instance = None
        
        
        
        self.get_start_funcs()
        # self.get_close_funcs()
        self.wrap_new()

        

    def get_start_funcs(self):
        for attr in dir(self.cog):
            attr = getattr(self.cog, attr, None)
            if(res := getattr(attr, "init_func", None)):
                if(res):
                    self.startup_funcs.append(attr)
                    
        if(not self.startup_funcs):
            self.start_funcs_called = True

    def get_close_funcs(self):
        for attr in dir(self.cog):
            attr = getattr(self.cog, attr, None)
            if(res := getattr(attr, "close_func", None)):
                if(res):
                    self.closing_funcs.append(attr)

    def wrap_new(self):
        og = self.cog.__new__
        
            
        
        async def wrapper(cls, *args, **kwargs):
            instance =  await og(cls, *args, **kwargs) # aobject
            self.instance = instance
            
            for func in self.startup_funcs:
                ogfunc = getattr(instance, func.__name__)
                
                def arg_wrapper(func): # This is retarded
                    async def func_wrapper(*args, **kwargs):
                        await func(*args, **kwargs) #im lazy
                        
                        af = True
                        for i, startup_func in enumerate(self.startup_funcs):
                            if(func.__name__ == startup_func[0].__name__):
                                self.startup_funcs[i][1] = True
                            if(not startup_func[1]):
                                af = False
                        if(af):
                            await self.main.primary.debug("All start_funcs for Cog '{}' were called".format(self.cog.name))
                            self.start_funcs_called = True
                        
                    return func_wrapper
                    
                func = arg_wrapper(ogfunc)
                func.__name__ = ogfunc.__name__
                func.init_func = ogfunc.init_func
                for i, startup_func in enumerate(self.startup_funcs):
                    if(isinstance(startup_func, list)):
                        continue
                    if(startup_func.__name__ == func.__name__):
                        self.startup_funcs[i] = [func, False] # l[1] is status if executed
                self.helper.start_funcs[func.init_func[1]] = func # bind method to __self__
            
            return instance
        
        self.cog.__new__ = wrapper
        
    # planning to add scheduled tasks here



# Independent object responsible for setting up Cogs and setting up their schedules
# Uses some main attributes, use setup() to setup
# ASSUMES EACH COG ONLY HAS 1 INSTANCE    
class SetupHelper(object):

    def __init__(self, main) -> None:
        self.main = main
        self.task_managers = []
        self.start_funcs = {}
        
        self.last_arg = 0
        
        og = self.main.client.on_ready
        
        
        async def wrap_client_on_ready(*args, **kwargs):
            await self.main.primary.debug("Running Cog start_funcs in order")
            await og(*args, **kwargs)
            order = sorted(list(self.start_funcs.keys()))
            for i in order:
                func = self.start_funcs[i]
                await self.main.primary.debug("Running {}".format(func))
                await func()
            # for taskmanager in self.tasks:
            #     funcs = taskmanager.startup_funcs
            #     for func in funcs:
            #         await func()
            #     taskmanager.start_funcs_inited = True
            #     self.main.primary.debug("Init function on cog '{}' executed".format(taskmanager.cog.name))
            
        
        self.main.client.on_ready  = wrap_client_on_ready
            
        
    
    def helpargs(self, name=None, desc=None, usage=None, hidden=False, shortdesc=None, showsubcat=False): #highly rigged function to assign function attributes as a decorator
        def wrapper(obj):
            obj.name = name
            obj.desc = desc
            obj.usage = usage
            obj.hidden = hidden
            if(not shortdesc):
                obj.shortdesc = desc
            else:
                obj.shortdesc = shortdesc
            return obj
        return wrapper
    
    
    def notifier(self, method):
        async def wrapper(*args, **kwargs):
            _self  = args[0] # self is arg 0
            _ctx = args[1] # context is arg 1
            await self.main.all_loggers["commands"][0].debug("command '{}' requested by user '{}'".format(method.__name__, _ctx.author.id))
            await method(*args, **kwargs)
        wrapper.__name__ = method.__name__
        return wrapper

    def attach_task_manager(self, cls):
        if(not (instance := getattr(cls, "task_manager", None))):
            instance = TaskManager(cls, self.main, self)
            cls.task_manager = instance
        return cls


    def init_func(self, arg):
        # my code is flawless shut up
        if(not isinstance(arg, int)):
            func = arg
            nums = list(self.start_funcs.keys())
            nums.append(self.last_arg + 1)
            self.last_arg += 1 
            func.init_func = [True, max(nums)]
            return func
        def wrapper(func):
            func.init_func = [True, arg]
            return func
        return wrapper

    def attach_blocker(self, method):
        async def wrapper(*args, **kwargs):
            _self  = args[0]
            _ctx = args[1] 
            if(not _self.task_manager.start_funcs_called):
                embed=discord.Embed(title="Category not loaded", description="please wait the the command category gets loaded!", color=0xff0000)
                await _ctx.send(embed=embed)
            else:
                await method(*args, **kwargs)
        wrapper.__name__ = method.__name__
        return wrapper
        
def setup(main):
    global setuphelper
    setuphelper = SetupHelper(main)
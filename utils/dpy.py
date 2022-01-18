from discord.ext import commands
import asyncio

class TaskManager(object):
    def __init__(self, cls, main, helper) -> None:
        self.main = main
        self.cog = cls
        self.helper = helper
        # self.commands = cls.__cog_commands__
        self.startup_funcs = []
        self.start_funcs_inited = False
        self.gather_init_funcs()
    
        
    def run_inits(self):
        for func in self.startup_funcs:
            func()

    def gather_init_funcs(self):
        for attr in dir(self.cog):
            attr = getattr(self.cog, attr, None)
            if(res := getattr(attr, "init_func", None)):
                if(res):
                    self.startup_funcs.append(attr)
    
class SetupHelper(object):

    def __init__(self, main) -> None:
        self.main = main
        self.tasks = []
        
        og = self.main.client.on_ready
        async def wrap_client_on_ready(*args, **kwargs):
            await og(*args, **kwargs)
            for taskmanager in self.tasks:
                funcs = taskmanager.startup_funcs
                for func in funcs:
                    await func()
                taskmanager.start_funcs_inited = True
                self.main.primary.debug("Init function on cog '{}' executed".format(taskmanager.cog.name))
            
        
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
        # print("wrapper")
        return wrapper

    def attach_task_manager(self, cls):
        instance = TaskManager(cls, self.main, self)
        cls.task_manager = instance
        self.tasks.append(instance)
        return cls


    def init_func(self, arg):
        # my code is flawless shut up
        if(not isinstance(arg, int)):
            func = arg
            func.init_func = True
            return func
        def wrapper(func):
            func.init_func = True
            return func
        return wrapper

    def attach_blocker(self, method):
        async def wrapper(*args, **kwargs):
            _self  = args[0]
            _ctx = args[1] 
            if(not _self.task_manager.start_funcs_inited):
                print("Not Inited!")
            else:
                await method(*args, **kwargs)
        wrapper.__name__ = method.__name__
        return wrapper
        
def setup(main):
    global setuphelper
    setuphelper = SetupHelper(main) 
from discord.ext import commands
import asyncio

class TaskManager(object):
    def __init__(self, cls, helper) -> None:
        self.cog = cls
        self.helper = helper
        # self.commands = cls.__cog_commands__
        self.startup_funcs = []
        self.inited = False
        self.start_funcs_inited = False
        self.gather_init_funcs()
        self.wrap_init()
    
        
        
    def wrap_init(self):
        _init = self.cog.__init__
        async def wrapper(*args, **kwargs):
            _self = args[0]
            await _init(*args, **kwargs)
            self.inited = True
            for task in self.helper.tasks:
                if(not task.inited):
                    break
            
            loop = asyncio.get_running_loop()
            
            for task in self.helper.tasks:
                for func in task.startup_funcs:
                    await func()
                await _self.main.primary.debug("Cog {} Initialized".format(task.cog.name))
                task.start_funcs_inited = True
            await _self.main.primary.debug("All command blockers removed".format(task.cog.name))
        self.cog.__init__ = wrapper
        
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

    def __init__(self) -> None:
        self.tasks = []
    
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
            await _self.main.all_loggers["commands"][0].debug("command '{}' requested by user '{}'".format(method.__name__, _ctx.author.id))
            await method(*args, **kwargs)
        wrapper.__name__ = method.__name__
        # print("wrapper")
        return wrapper

    def attach_task_manager(self, cls):
        instance = TaskManager(cls, self)
        cls.task_manager = instance
        self.tasks.append(instance)
        return cls


    def init_func(self, method):
        method.init_func = True # my code is flawless shut up
        return method

    def attach_blocker(self, method):
        async def wrapper(*args, **kwargs):
            _self  = args[0]
            _ctx = args[1] 
            print("here", _self.task_manager.start_funcs_inited)
            if(not _self.task_manager.start_funcs_inited):
                print("Not Inited!")
            else:
                await method(*args, **kwargs)
        wrapper.__name__ = method.__name__
        return wrapper
        
setuphelper = SetupHelper()    



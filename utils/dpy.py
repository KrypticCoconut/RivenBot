
from discord.ext import commands
import asyncio
import discord
import copy

class SpecialFunc(object):
    def __init__(self, func, local_order, global_order) -> None:
        self.callback = func
        self.called = False
        self.local_order = local_order
        self.global_order = global_order

class TaskManager(object):
    
    def __init__(self, cls, main, helper) -> None:
        self.main = main
        self.cog = cls
        self.helper = helper
        
        self.startup_funcs = []
        self.start_funcs_called = False
        
        self.close_funcs = []

        
        # self.local_order = {}
        # self._local_latest = 0
        # self.closing_funcs = []
        # self.get_close_funcs()
        
        # self.instance = None
        self.wrap_new()


    def wrap_new(self):
        og = self.cog.__new__ # the special funcs are instance attrs so they need to be binded to __self__ before they can be run which happens right after __new__

        async def wrapper(cls, *args, **kwargs):
            instance =  await og(cls, *args, **kwargs) # aobject
            
            local_order_dict = {}
            for attr in dir(self.cog):
                attr = getattr(instance, attr, None)
                if(isinstance(res := getattr(attr, "start_func", None), list)):
                    if(res):
                        local_order, global_order = res
                        if(not local_order):
                            k = list(local_order_dict.keys())
                            k.append(0)
                            local_order = max(k) + 1 # basically the next one
                            
                        
                        def arg_wrapper(func): # This is retarded
                            async def func_wrapper(*args, **kwargs):
                                stat = func_wrapper.stat
                                await func(*args, **kwargs) #im lazy
                                stat.called =  True
                                self.main.primary.debug("start func '{}' executed".format(func))
                                for startup_func in self.startup_funcs:
                                    if(not startup_func.called):
                                        return
                                self.start_funcs_called = True
                                    
                                await self.main.primary.debug("All start_funcs for Cog '{}' were called".format(self.cog.name))
                                
                            return func_wrapper
                        
                        func = arg_wrapper(attr)
                        func.__name__ = attr.__name__
                        func.start_func = attr.start_func
                        
                        special_func = SpecialFunc(func, local_order, global_order)
                        func.stat = special_func
                        if(local_order_dict.get(local_order)):
                            raise Exception("Cannot have 2 starting functions with point [{}] in local_order dict {}".format(local_order, local_order_dict))
                        local_order_dict[local_order] = special_func
                        


            if(list(local_order_dict.keys()) == []):
                await self.main.primary.debug("No start funcs for Cog '{}' were defined".format(self.cog.name))
                self.start_funcs_called = True
            else:
                self.startup_funcs = list(map(lambda kvp: kvp[1], sorted(local_order_dict.items(), key=lambda kvp: kvp[0])))
            self.helper.start_local_orders.append(copy.copy(self.startup_funcs)) # fuck off
            
            # close order --------------------------------------------------------------------------------------------------------------------------
            local_order_dict = {}
            for attr in dir(self.cog):
                attr = getattr(instance, attr, None)
                if(isinstance(res := getattr(attr, "close_func", None), list)):
                    if(res):
                        local_order, global_order = res
                        if(not local_order):
                            k = list(local_order_dict.keys())
                            k.append(0)
                            local_order = max(k) + 1 # basically the next one
                            
                        def arg_wrapper(func): # This is retarded
                            async def func_wrapper(*args, **kwargs):
                                stat = func_wrapper.stat
                                await func(*args, **kwargs) #im lazy
                                stat.called =  True
                                self.main.primary.debug("close func '{}' executed".format(func))
                                for close_func in self.close_funcs:
                                    if(not close_func.called):
                                        return
                                await self.main.primary.debug("All close_funcs for Cog '{}' were called".format(self.cog.name))
                                
                            return func_wrapper
                        
                        func = arg_wrapper(attr)
                        func.__name__ = attr.__name__
                        func.close_func = attr.close_func

                        special_func = SpecialFunc(func, local_order, global_order)
                        func.stat = special_func
                        if(local_order_dict.get(local_order)):
                            raise Exception("Cannot have 2 closing functions with point [{}] in local_order dict {}".format(local_order, local_order_dict))
                        local_order_dict[local_order] = special_func
                        


            self.close_funcs = list(map(lambda kvp: kvp[1], sorted(local_order_dict.items(), key=lambda kvp: kvp[0])))
            self.helper.close_local_orders.append(copy.copy(self.close_funcs)) # fuck off
            
            
            return instance
            
        self.cog.__new__ = wrapper



# Independent object responsible for setting up Cogs and setting up their schedules
# Uses some main attributes, use setup() to setup
# ASSUMES EACH COG ONLY HAS 1 INSTANCE
# also btw this is such terrible code that i dont even know how this works just a week later
class SetupHelper(object):

    def __init__(self, main) -> None:
        
                            # if(global_order in self.helper._start_globals_indexes):
                                # raise Exception("Cannot have 2 functions with point [{}] in global_orders list {}".format(global_order, self._start_globals_indexes))
        self.main = main
        self.task_managers = []
        
        self.start_local_orders = []
        self.close_local_orders = []
        
        og = self.main.client.on_ready
        
        
        async def wrap_client_on_ready(*args, **kwargs):
            start_globals_indexes = []
            close_global_indexes = []
            
            for local_order in self.start_local_orders:
                for stat in local_order:
                    if(stat.global_order):
                        start_globals_indexes.append(stat.global_order)
            for local_order in self.close_local_orders:
                for stat in local_order:
                    if(stat.global_order):
                        close_global_indexes.append(stat.global_order)
                        
            start_globals_indexes = sorted(start_globals_indexes)
            close_global_indexes = sorted(close_global_indexes)
            
            #compile order for start funcs

            start_run_order = []
            for anchor in start_globals_indexes:
                for order_num, order in enumerate(self.start_local_orders):
                    prev = []
                    found = False
                    for last_place, stat in enumerate(order):
                        prev.append(stat)
                        if(stat.global_order == anchor):
                            found = True
                            break
                    if(not found):
                        continue
                    
                    for global_anchor in start_globals_indexes:
                        if(not global_anchor > anchor):
                            continue
                        if(global_anchor in map(lambda x: x.global_order, prev)):
                            raise Exception("Global anchor #{} locally needs to be called before global anchor #{} - illegal call".format(global_anchor, anchor)) 
                    start_run_order.extend(self.start_local_orders[order_num][:last_place+1])
                    del self.start_local_orders[order_num][:last_place+1]

            
            for order_num, order in enumerate(self.start_local_orders):
                start_run_order.extend(order)
                del self.start_local_orders[order_num][:len(order)]
                    
            # yeehaw copy paste code
            # compile order for close funcs
            close_run_order = []
            for anchor in close_global_indexes:
                for order_num, order in enumerate(self.close_local_orders):
                    prev = []
                    found = False
                    for last_place, stat in enumerate(order):
                        prev.append(stat)
                        if(stat.global_order == anchor):
                            found = True
                            break
                    if(not found):
                        continue
                    
                    for global_anchor in close_global_indexes:
                        if(not global_anchor > anchor):
                            continue
                        if(global_anchor in map(lambda x: x.global_order, prev)):
                            raise Exception("Global anchor #{} locally needs to be called before global anchor #{} - illegal call".format(global_anchor, anchor)) 
                    close_run_order.extend(self.close_local_orders[order_num][:last_place+1])
                    del self.close_local_orders[order_num][:last_place+1]

            
            for order_num, order in enumerate(self.start_local_orders):
                close_run_order.extend(order)
                del self.close_local_orders[order_num][:len(order)]
                    
            
            self.close_order = close_run_order
            self.start_order = start_run_order
    
            for func in start_run_order:
                await func.callback()
                
            await og(*args, **kwargs)
            
        
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
    
    
    def notifier(self, commandcls):
        method = commandcls._callback
        async def wrapper(self, ctx, *args):
            await self.main.all_loggers["commands"][0].debug("command '{}' requested by user '{}'".format(method.__name__, ctx.author.id))
            await method(self, ctx, *args)
        wrapper.__name__ = method.__name__
        commandcls._callback = wrapper
        return commandcls

    def attach_task_manager(self, cls):
        if(not (instance := getattr(cls, "task_manager", None))):
            instance = TaskManager(cls, self.main, self)
            cls.task_manager = instance
        return cls
    
    
    # local order does not care about global order, while global order does
    # local orders that accur before the global orders are sort of anchored to global orders
    def global_start_func(self, global_order=None, local_order=None): # global func -> arg1 is the local order and arg2 is the global order
        # my code is flawless shut up
        
        if(not isinstance(global_order, int)):
            raise Exception("Global order not provided")
        
        def wrapper(func):
            func.start_func = [local_order, global_order]
            
            return func
        return wrapper
    
    def cog_start_func(self, arg=None): # cof func -> arg1 is local order
        # my code is flawless shut up
        if(not isinstance(arg, int)):
            func = arg
            func.start_func = [None, None]
            return func
        
        def wrapper(func):
            func.start_func = [arg, None]
            return func
        return wrapper
    
    
    def global_close_func(self, global_order=None, local_order=None): # global func -> arg1 is the local order and arg2 is the global order
        # my code is flawless shut up
        
        if(not isinstance(global_order, int)):
            raise Exception("Global order not provided")
        
        def wrapper(func):
            func.close_func = [local_order, global_order]
            
            return func
        return wrapper
    
    def cog_close_func(self, arg=None): # cof func -> arg1 is local order
        # my code is flawless shut up
        if(not isinstance(arg, int)):
            func = arg
            func.close_func = [None, None]
            return func
        
        def wrapper(func):
            func.close_func = [arg, None]
            return func
        return wrapper
    
    
    # def close_func(self, arg):
    #     # my code is flawless shut up
    #     if(not isinstance(arg, int)):
    #         func = arg
    #         nums = list(self.close_funcs.keys())
    #         nums.append(self.last_arg + 1)
    #         self.last_arg += 1 
    #         func.close_func = max(nums)
    #         return func
    #     def wrapper(func):
    #         func.close_func = arg
    #         return func
    #     return wrapper

    def attach_blocker(self, commandcls):
        method = commandcls._callback
        async def wrapper(self, ctx, *args):
            if(not self.task_manager.start_funcs_called):
                embed=discord.Embed(title="Category not loaded", description="please wait the the command category gets loaded!", color=0xff0000)
                await ctx.send(embed=embed)
            else:
                await method(self, ctx, *args)
        wrapper.__name__ = method.__name__
        commandcls._callback = wrapper
        return commandcls
    
    async def call_close_funcs(self):
        await self.main.primary.debug("Running Cog close functions in order")
        for func in self.close_order:
            await func.callback()
    
def setup(main):
    global setuphelper
    setuphelper = SetupHelper(main)
    return setuphelper
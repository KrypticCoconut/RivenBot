
from asyncore import read
import re
from turtle import update
from types import TracebackType
from utils.misc import aobject
import asyncio
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy

from utils.modules.caches.nocache import NoCache
from utils.modules.caches.cache import Cache
        
class ValueHolder:
    def __init__(self, val, pkey, null) -> None:
        self.val  = val
        self.pkey = pkey
        self.null = null
        self.reference_nodes = []

# A cache has 4 main functions
# get_row - returns and caches conf, adds a conf if one does not exist already
# addconf - adds row, specfic cache usage
# del_row - can delete rows, check specific command usage 
# change_wrapper - called when a change in the cache or runtime_function occurs, it should be used to notify the user of runtime cache changes that apply globally 
class SqlCacheParent(aobject):

    async def add_tree_conf(self, tree_conf, curr_table, target_table, target_pkey, edit=False):  # add a conf from a given root, should be used a very low level
        cache = self.caches[curr_table]
        table = cache.table
        pkey_attr = cache.primary_key_attr_str

        pkey = tree_conf[pkey_attr]
        curr_conf = {}

        for column in table.columns: # pull columns for current table from the tree conf
            if(column.name in tree_conf.keys()):
                curr_conf[column.name] = tree_conf[column.name]
        
        if(edit):
            _conf = await cache.get_row(pkey, conf = curr_conf, cache=False)
            conf = _conf.curr_dict
            old = False
            for attr in conf.keys():
                if(attr in curr_conf.keys()):
                    if(not curr_conf[attr] == conf[attr]): # the new conf was not the one used, the old one was used
                        old = True
                        conf[attr] = curr_conf[attr]
                        
            if(old):
                if(isinstance(cache, NoCache)):
                    await _conf.update()
                elif(isinstance(cache, Cache)):
                    pass
            conf = _conf
                
        else:
            conf = await cache.get_row(curr_conf[pkey_attr], conf=curr_conf)
        
        pkey = conf[pkey_attr]
        ret_conf = conf
        if((not pkey == target_pkey) or (not cache.table_name == target_table)):
            ret_conf = None
        
                
        
        for name, table in self.main.sqlapi.tables.items():
            if(name in tree_conf.keys()):
                attr = tree_conf[name]
                if(isinstance(attr, list)):
                    for _attr in attr:
                        ret = await self.add_tree_conf(_attr, name, target_table, target_pkey, edit=edit)
                        if(ret):
                            ret_conf = ret

                else:
                    ret = await self.add_tree_conf(attr, name, target_table, target_pkey, edit=edit)
                    if(ret):
                        ret_conf = ret
                        
        return ret_conf
                    
    
    async def closing_func(self):
        for cache in self.caches.values():
            if(getattr(cache, "commit_all", None)):
                await cache.commit_all()
    
    async def __init__(self, main):
        self.main = main
        self.sqlapi = self.main.sqlapi
        self.lock = self.sqlapi.lock
        self.caches = {}
        main.caches = self.caches
        
        for table in list(main.sqlapi.tables.values()):

            if(getattr(table, "hidden", None)):
                continue
            cachelen = table.cachelen
            if(cachelen == 0):
                cache = await NoCache(self.main, table, self)
            else:

                cache = await Cache(self.main, table, self)
            self.caches[table.name] = cache

            self.main.inject_globals(table.name, cache)
        
        
        
        # ------------------------- example usage of nocache databases -----------------------------
        # users = self.caches["users"]
        # blogs = self.caches["blogs"]

        # # # ------------ GETTING ------------ 
        # name1 = await users.get_row("name1", conf= {"name": "name1", "age": 12}, root = "users")
        # name2 = await users.get_row("name2", conf= {"name": "name2", "age": 12}, root = "users")
       
        # blog = await blogs.get_row("sqlalchemy sucks", conf = {"name": "name1", "age": 4, "blogs": {"title": "sqlalchemy sucks", "author_name": "name1"}}, root = "users")
        
        # await blog.delete()
        
        # name1["name"] = 'name1changed'
        # await name1.update()

        # ------------------------- example usage of cache databases -----------------------------
        #assumes cahclen 1 for bpth tables
        # users = self.caches["users"]
        # blogs = self.caches["blogs"]
        
        # name1 = await users.get_row("name1", conf= {"name": "name1", "age": 12, "blogs": {'author_name': 'name1', 'title': 'test'}}, root = "users")
        # blog = await blogs.get_row("test")
        # name2 = await users.get_row("name2", conf = {"name": "name2", "age": 12})
        # await name2.change('name', "name2_changed")
        # name1 = await users.get_row("name1")
        
        # await blog.delete()
        
        
MOD = SqlCacheParent
NAME = "sqlcache"
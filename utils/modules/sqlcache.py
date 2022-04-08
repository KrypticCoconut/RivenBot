
from asyncore import read
from turtle import update
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

    async def add_tree_conf(self, tree_conf, curr_table, edit=False):  # add a conf from a given root, should be used a very low level
        cache = self.caches[curr_table]
        table = cache.table
        pkey_attr = cache.primary_key_attr_str

        pkey = tree_conf[pkey_attr]
        curr_conf = {}
        
        
        for column in table.__table__.columns:
            if(column.name in tree_conf.keys()):
                curr_conf[column.name] = tree_conf[column.name]
        
        if(edit):
            conf = await cache.get_row(pkey, conf = curr_conf, cache=False)
            old = False
            for attr in conf.keys():
                if(attr in curr_conf.keys()):
                    if(not curr_conf[attr] == conf[attr]): # the new conf was not the one used, the old one was used
                        old = True
                        conf[attr] = curr_conf[attr]
            if(old):
                if(isinstance(cache, NoCache)):
                    await cache._update_row(pkey, conf, pkey=True)
                elif(isinstance(cache, Cache)):
                    pass
                
        else:
            await cache.add_conf(curr_conf)
            
            
        for name, relationship in inspect(table).relationships.items():
            if(name in tree_conf.keys()):
                attr = tree_conf[name]
                tablename = relationship.target.name
                
                if(isinstance(attr, list)):
                    for _attr in attr:
                        await self.add_tree_conf(_attr, tablename, edit=edit)
                else:
                    await self.add_tree_conf(attr, tablename, edit=edit)
    
    async def closing_func(self):
        for cache in self.caches.values():
            if(getattr(cache, "commit_all", None)):
                await cache.commit_all()
    
    async def __init__(self, main):
        self.main = main
        self.sqlapi = self.main.sqlapi
        self.session = self.sqlapi.session
        self.lock = self.sqlapi.lock
        self.caches = {}
        main.caches = self.caches
        
        for table in list(main.sqlapi.tables.values()):

            if(getattr(table, "hidden", None)):
                continue
            cachelen = table.cachelen
            readonly = table.readonly
            if(cachelen == 0):
                cache = await NoCache(self.main, table, self)
            else:
                cache = await Cache(self.main, table, self)
                # cache = Cache(self.main, table. self)
            self.caches[table.__tablename__] = cache

            self.main.inject_globals(table.__tablename__, cache)
        
        
        
        # ------------------------- example usage of nocache databases -----------------------------
        # users = self.caches["users"]
        # blogs = self.caches["blogs"]

        # # ------------ GETTING ------------ 
        # name1 = await users.get_row("name1", conf= {"name": "name1", "age": 12}, root = "users")
        # name2 = await users.get_row("name2", conf= {"name": "name2", "age": 12}, root = "users")
       
        # blog = await blogs.get_row("sqlalchemy sucks", conf = {"name": "name1", "age": 4, "blogs": {"title": "sqlalchemy sucks", "author_name": "name1"}}, root = "users", edit=True)
        # # edit changes age 12 to 4, if edit = false then it can only add rows, not edit
        
        # stmt = select(users.table).where(users.table.age == 4)
        # print(await users.get_row(stmt))
        # # ------------ UPDATING ------------ 
        # blog["title"] =  "sqlalchemy is good nvm" # even pkey works
        # await blog.update()
        
        # # ALTERNATIVE
        # # blog["title"] = "sqlalchemy is good nvm"
        # # await blogs._update_row(blog.original["title"], blog, pkey=True, change_wrapper=True)
        
        
        # name2["name"] = "name3" # you can change pkeys
        # await name2.update()
        
        # # ------------ DELETING ------------
        
        # await name2.delete()
        
        # ALTERNATIVE
        # stmt = select(users.table).where(users.table.name == "name3")
        # await users.del_row(stmt)
        
        # -----------------------------------------------------
        # ------------------------ END ------------------------ 
        # -----------------------------------------------------
        
        
        # ------------------------- example usage of cache databases -----------------------------
        # users = self.caches["users"]
        # blogs = self.caches["blogs"]
        
        # name1 = await users.get_row("name1", conf= {"name": "name1", "age": 12}, root = "users")
        # await name1.change("name", "name3")
        # name2 = await users.get_row("name2", conf= {"name": "name2", "age": 12}, root = "users")
        
        # print(users.cache)
        
MOD = SqlCacheParent
NAME = "sqlcache"
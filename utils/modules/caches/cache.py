
from distutils.command.config import config
import re
from sys import prefix
from types import NoneType
from unittest.mock import patch
from utils.misc import aobject
import asyncio
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy

class dict_wrapper(dict):
    def __init__(self, *args, **kwargs) -> None:
        self.last_commit = args[0]
        self.cache = kwargs["cache"]
        self.session = self.cache.session
        self.pkey_attr = self.cache.primary_key_attr_str
        self.main = kwargs["main"]
        self.change_wrapper = self.cache.change_wrapper
        dict.__init__(self, self.last_commit)
        
    async def change(self, key, value):            
        old = dict(self) # inneficient af
        self[key] = value
        
        if(self.change_wrapper):
            payload= await self.change_wrapper(old[self.pkey_attr], self[self.pkey_attr])
            if(payload): await payload(self.cache, old, self, [])        
    async def delete(self):
        await self.cache.del_row(self.last_commit[self.pkey_attr])

class DoesNotExist():
    pass


class Node:
    def __init__(self, key, val, pkey=True):
        self.key = key  # key can be primary key
        self.val = val # val can be value
        self.next = None
        self.prev = None

             
class Cache(aobject):
    async def __init__(self, main, table, parent):
        self.main = main
        self.parent = parent
        self.sqlapi = main.sqlapi
        self.lock = self.sqlapi.lock # locks shouldnt be used at this level
        self.session = self.sqlapi.session

        self.table = table
        self.table_name = table.__tablename__
        self.cache_nulls = self.table.cache_nulls
        self.cachelen = self.table.cachelen

        for column in table.__table__.columns:
            if(column.primary_key):
                self.primary_key_attr_str = column.name
                self.primary_key_attr = getattr(self.table, column.name)        
        
        self.logger = self.main.all_loggers["database"][0]
        self.add_tree_conf = parent.add_tree_conf
        self.change_wrapper = main.cache_wrapper_extender.cache_wrappers.get(self.table_name, None)
        
        
        self.cache = dict()
        # a none in the cache means the row does not exist, and is not added
        # a {} in the cache means the row will be deleted
        
        self.head = Node(0, 0)
        self.tail = Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head
        
        
    async def get_row(self, primary_key, conf = None, root = None, edit = False, **kwargs): # can query using only a primary key
        
        if(primary_key in self.cache.keys()):
            cached = self.cache[primary_key]
            if(isinstance(cached, DoesNotExist)): # If it a cached none value
                if(not conf): # same code as if value does not exist
                    await self.llist_node(primary_key)
                    return cached
                if(not root):
                    await self.llist_node(primary_key)
                    await self.add_conf(conf, check=False)
                    
                    stmt = select(self.table).where(self.primary_key_attr == primary_key)
                    async with self.session.begin():
                        results = await self.session.execute(stmt)
                    result  = self.sqlapi.deserialize_object(results.scalars().first())
                                        
                    self.cache[primary_key] = result
                    return self.cache[primary_key]
                    
                else:
                    await self.add_tree_conf(conf, root, edit=edit)

                    stmt = select(self.table).where(self.primary_key_attr == primary_key)
                    async with self.session.begin():
                        results = await self.session.execute(stmt)
                    result  = self.sqlapi.deserialize_object(results.scalars().first())
                    
                    return self.cache[primary_key] # sketchy code
            else:
                await self.llist_node(primary_key)
                return cached
        
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        async with self.session.begin():
            results = await self.session.execute(stmt)
        result  = results.scalars().first()
        
        if(not result):
            if(not conf):
                if(self.cache_nulls):
                    self.cache[primary_key] = DoesNotExist()
                    return self.cache[primary_key]
                else:
                    return DoesNotExist()
            if(not root):
                await self.add_conf(conf, check=False)
                result = await self.get_row(primary_key)
                return result
            else:
                await self.add_tree_conf(conf, root, edit=edit)
                result = await self.get_row(primary_key)
                return result
        
        result = dict_wrapper(await self.sqlapi.deserialize_object(result), main=self.main, cache=self)
        
        if(len(self.cache) >= self.cachelen):
            node = self.head.next
            await self.update(node)
            await self.remove_node(node)
            del self.cache[node.key]
        
        self.cache[primary_key] = result
        node = Node(primary_key, self.cache[primary_key])
        await self.add_node(node)
        
        return self.cache[primary_key]

        
        
    async def add_conf(self, conf, check=True): # check if row exists, if doesnt add config, can be used on a lower level
        
        if(check):
            primary_key = conf[self.primary_key_attr_str]
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
            
            async with self.session.begin():
                results = await self.session.execute(stmt)
        
            result = results.scalars().first()
            
            if(result):
                return
        
        obj = await self.sqlapi.serialize_dict(conf, self.table.__tablename__)
        async with self.session.begin():
            self.session.add(obj)
            
        
        async with self.session.begin():
            stmt = select(self.table).where(self.primary_key_attr == conf[self.primary_key_attr_str])
            result = await self.session.execute(stmt)
            
        result = result.scalars().first()
        conf = await self.sqlapi.deserialize_object(result)
        
        await self.logger.debug("Added row with primary key {} in table {} with conf {}".format(conf[self.primary_key_attr_str], self.table_name, conf))
        
        
        if(self.change_wrapper):
            payload= await self.change_wrapper(None, conf[self.primary_key_attr_str])
            if(payload): await payload(self, {}, conf, [])

    # takes pkey as input
    # if check is enabled it will check if a row already exists
    async def del_row(self, primary_key, check=True):
        if(primary_key in self.cache.keys()):
            if(self.cache[primary_key] == {}):
                return
            if(self.change_wrapper):
                payload= await self.change_wrapper(primary_key, None)
                if(payload): await payload(self, self.cache[primary_key], {}, [])
            self.cache[primary_key] = {}
            return
        
        payload = self.change_wrapper(primary_key)
        if(payload or check):
            conf = await self.get_row(primary_key)
            if(isinstance(conf, DoesNotExist)):
                return
            else:
                self.cache[primary_key] = {}
                if(payload):
                    payload= await self.change_wrapper(primary_key, None)
                    if(payload): await payload(self, self.cache[primary_key], {}, [])
                return

        else:
            if(len(self.cache) >= self.cachelen):
                node = self.head.next
                await self.update(node)
                await self.remove_node(node)
                del self.cache[node.key]
                
            node = Node(primary_key, {})
            await self.add_node(node)
            return
            
    
    async def update(self, node): # commits node
        primary_key = node.key
        conf = node.val
        
        if(isinstance(conf, DoesNotExist)):
            return
        elif(conf != {}):
                    
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
            async with self.session.begin():
                result = await self.session.execute(stmt)
                result = result.scalars().first()

                # we already have access to prev and current configs without extra shit, so we dont need to worry about other stuff
                
                primary_key = getattr(result, self.primary_key_attr_str)
                cdict = {}
                ndict = {}
                changed = []
                for column in self.table.__table__.columns:
                    name = column.name
                    cval = getattr(result, name)
                    nval = conf[name]
                    
                    cdict[name]  = cval
                    ndict[name] = nval
                    
                    
                    if(cval != nval): changed.append(name)

                if(changed):
                    for name in changed:
                        setattr(result, name, ndict[name])
                    
                    await self.logger.debug("Changed row with primary key {} in table {} from {} to {}".format(primary_key, self.table_name, cdict, ndict))
                    

        else:
      
            stmt = delete(self.table).where(self.primary_key_attr == primary_key)
            async with self.session.begin():
                await self.session.execute(stmt)
            
            await self.logger.debug("Deleted row with primary key {} in table {}".format(primary_key, self.table_name))

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    # CACHE FUNCS
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    async def remove_node(self, node):
        p = node.prev
        n = node.next
        p.next = n
        n.prev = p  
        
    async def add_node(self, node):
        p = self.tail.prev
        p.next = node
        self.tail.prev = node
        node.prev = p
        node.next = self.tail
        
    async def llist_node(self, primary_key):
        current = self.head
          
        while True:
              
            if current.key == primary_key:
                node = current
                await self.remove_node(node)
                await self.add_node(node)
                break
              
            else:
                current = current.next    
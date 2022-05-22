
from distutils.command.config import config
import re
from sys import prefix
from traceback import print_tb
from types import NoneType
from unittest.mock import patch
from utils.misc import aobject
import asyncio
from sqlalchemy import delete, true, insert, update
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy
import copy

class dict_wrapper:
    def __init__(self, old_dict, cache, main) -> None:
        self.cache = cache
        self.engine = self.cache.engine
        self.pkey_attr = self.cache.primary_key_attr_str
        self.main = main
        self.change_wrapper = self.cache.change_wrapper
        self.cached = False
        self.old_dict = old_dict
        self.curr_dict = copy.deepcopy(old_dict)
        
        
    def __getitem__(self, key):
        return self.curr_dict[key]
    
    def __setitem__(self, key, val):
        self.curr_dict[key] = val
    
    def __delitem__(self, key):
        del self.curr_dict[key]
    
    async def change(self, key, value):            
        old = copy.deepcopy(self.curr_dict)
        self.curr_dict[key] = value
        if(key == self.pkey_attr and self.cached): # if cached and pkey is changed, change name in cache
            node  = self.cache.cache[old[self.pkey_attr]]
            node.key = value
            del self.cache.cache[old[self.pkey_attr]]
            self.cache.cache[value] = node
        if(self.change_wrapper): await self.change_wrapper.update(old, self.curr_dict)

    async def delete(self):
        await self.cache.del_row(self[self.pkey_attr])

class Node:
    def __init__(self, key, val):
        self.key = key 
        self.val = val
        self.next = None
        self.prev = None


class Cache(aobject):
    async def __init__(self, main, table, parent):
        self.main = main
        self.parent = parent
        self.sqlapi = main.sqlapi
        self.lock = self.sqlapi.lock # locks shouldnt be used at this level
        self.engine = main.sqlapi.engine
        self.table = table
        self.table_name = table.name
        self.cachelen = self.table.cachelen

        for column in table.columns:
            if(column.primary_key):
                self.primary_key_attr_str = column.name
                self.primary_key_attr = getattr(self.table.c, column.name)
        
        self.logger = self.main.all_loggers["database"][0]
        self.add_tree_conf = parent.add_tree_conf
        self.change_wrapper = main.cache_wrapper_extender.cache_wrappers.get(self.table_name, None)
        if(self.change_wrapper):
            self.change_wrapper.cache = self
        
        self.cache = dict()
        
        self.head = Node(0, 0)
        self.tail = Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head
    
    async def _add_conf_node(self, node): # adds a node to the cache
        if(len(self.cache) >= self.cachelen):
            _node = self.head.next
            await self.update(_node)
            await self.remove_node(_node)
            del self.cache[_node.key]
        self.cache[node.key] = node
        await self.add_node(node)
        
        
    async def get_row(self, primary_key, conf = None, root = None, edit = False, cache= True, **kwargs): # can query using only a primary key
        
        if(primary_key in self.cache.keys()):
            node = self.cache[primary_key]
            await self.llist_node(node)
            return node.val
        
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        async with self.engine.begin() as conn:
            results = await conn.execute(stmt)
        obj  = results.first()
        
        if(not obj):
            if(not conf):
                return None
            if(not root):
                result = await self.add_row(conf, check=False)
                if(cache):
                    result.cached = True
                    node = Node(primary_key, result)
                    await self._add_conf_node(node)
                return result
            else:
                result = await self.add_tree_conf(conf, root, self.table_name, primary_key, edit=edit)
                if(cache):
                    result.cached = True
                    node = Node(primary_key, result)
                    await self._add_conf_node(node)
                return result
        
        result = dict_wrapper(await self.sqlapi.deserialize_object(obj, tablename= self.table_name), main=self.main, cache=self)
        if(cache):
            node = Node(primary_key, result)
            await self._add_conf_node(node)
        
        return result

        
        
    async def add_row(self, conf, check=True): # check if row exists, if doesnt add config, can be used on a lower level
        
        if(check):
            primary_key = conf[self.primary_key_attr_str]
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
            
            async with self.engine.begin() as conn:
                results = await conn.execute(stmt)
        
            result = results.first()
            
            if(result):
                return False
        
        stmt = insert(self.table).values(conf).returning(self.table)
        async with self.engine.begin() as conn:
            result = await conn.execute(stmt)
            
        result = result.first()
        conf = await self.sqlapi.deserialize_object(result, tablename=self.table_name)
        
        await self.logger.debug("Added row {} in table {}".format(conf, self.table_name))
        
        
        if(self.change_wrapper): await self.change_wrapper.add(conf)
        return dict_wrapper(conf, self, self.main)

    # takes pkey as input
    # retun false if nothing is deleted
    async def del_row(self, primary_key):
        prev_conf = None
        new_conf = None
        if(primary_key in self.cache.keys()):
            node = self.cache[primary_key]
            new_conf = node.val.curr_dict
            prev_conf = node.val.old_dict
            await self.remove_node(node)
            del self.cache[primary_key]
            primary_key = prev_conf[self.primary_key_attr_str]
            
            stmt = delete(self.table).where(self.primary_key_attr==primary_key)
            async with self.engine.begin() as conn:
                await conn.execute(stmt)
                
            if(self.change_wrapper):
                await self.change_wrapper.delete(new_conf)
            await self.logger.debug("Deleted row with config {} in table {}".format(prev_conf, self.table_name))
            return prev_conf, new_conf

        stmt = delete(self.table).where(self.primary_key_attr==primary_key).returning(self.table)
        async with self.engine.begin() as conn:
            result = await conn.execute(stmt)
        
        result = result.first()
        if(not result):
            return False
        else:
            prev_conf = await self.sqlapi.deserialize_object(result, tablename=self.table_name)
            new_conf = prev_conf
            
        if(self.change_wrapper): await self.change_wrapper.delete(new_conf)
        await self.logger.debug("Deleted row with config {} in table {}".format(prev_conf, self.table_name))

        return prev_conf, new_conf


            
    
    async def update(self, node): # commits node

        async with self.engine.begin() as conn:

            

            cdict = node.val.old_dict
            ndict = node.val.curr_dict

            changed = []
            for column in self.table.columns:
                name = column.name
                
                cval = cdict[name]
                nval = ndict[name]
                if(cval != nval): changed.append(name)

            if(changed):
                
                stmt = update(self.table).where(self.primary_key_attr == cdict[self.primary_key_attr_str]).values(**ndict)
                async with self.engine.begin() as conn:
                    await conn.execute(stmt)
                await self.logger.debug("Changed row from {} to {} in table {}".format(cdict, ndict, self.table_name))
                



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
        
    async def llist_node(self, node):

        await self.remove_node(node)
        await self.add_node(node)

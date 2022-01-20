
from linecache import cache
from logging import root
import re
from tkinter import N
from utils.misc import aobject
import asyncio
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect

class Node:
    def __init__(self, key, val):
        self.key = key  # key can be primary key
        self.val = val # val can be value
        self.next = None
        self.prev = None
        
        
        
class SqlCache(aobject):
    async def __init__(self, main, table, parent, cachelen=20) -> None:
        self.main = main
        self.parent = parent
        self.sqlapi = main.sqlapi
        self.queue = self.sqlapi.queue
        self.table = table
        self.table_name = table.__tablename__
        
        for column in table.__table__.columns:
            if(column.primary_key):
                self.primary_key_attr = getattr(self.table, column.name) #i think im dumb
        
        self.cachelen = cachelen
        self.cache = dict()
        self.head = Node(0, 0) # initialize hidden and and start of linked list
        self.tail = Node(0, 0)
        self.head.next = self.tail # connect head to teal
        self.tail.prev = self.head

    def _get_relationship_from_root(self, obj, table, target_table, pkey): # not worth using
        if(table.__tablename__ == target_table):
            if(isinstance(obj, list)):
                for o in obj:
                    for column in table.__table__.columns:
                        if(column.primary_key):
                            self.primary_key_attr = getattr(self.table, column.name)
                return obj
        for name, relationship in inspect(table).relationships.items():
            inst_relation = getattr(obj, name)
            
            res = self._get_relationship_from_root(inst_relation, relationship.mapper.class_, target_table, pkey)
            if(res):
                return res
        return None

    async def get_row(self, primary_key: int, root = None, conf = None):
        # root indicates the starting table containing the primary key linking it to other tables in case a new one needs to be created
        if(primary_key in self.cache.keys()):
            await self.llist(primary_key)
            return self.cache[primary_key]
        
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        
        results = await self.queue.add(self.sqlapi.query_obj, [stmt]) 
        result  = results.scalars().first()
        if(not result):
            if(not root):
                return None
            if(not conf):
                obj = await self.build_object(primary_key, root=root)
            else:
                obj = await self.sqlapi.serialize_dict(conf, root)
            await self.queue.add(self.sqlapi.add_obj, [obj])
            await self.queue.add(self.sqlapi.expire, [obj]) # expire object sdo the next get_conf dont pull the child tables
            result = await self.get_row(primary_key, root, conf)
            # It isnt worth calculating table from object, if given a complex root, calculation cost is much more expensive than just querying once
            return result
                    
        if(len(self.cache) >= self.cachelen):
            node = self.head.next
            await self.commit(node)
            await self.remove(node)
            del self.cache[node.key]
        
        conf  = await self.sqlapi.deserialize_object(result)
        self.cache[primary_key] = conf
        node = Node(primary_key, conf)
        await self.add(node)
        return conf
        
    async def llist(self, primary_key):
        current = self.head
          
        while True:
              
            if current.key == primary_key:
                node = current
                await self.remove(node)
                await self.add(node)
                break
              
            else:
                current = current.next    

    async def add(self, node):
        p = self.tail.prev
        p.next = node
        self.tail.prev = node
        node.prev = p
        node.next = self.tail
    
    async def remove(self, node):
        p = node.prev
        n = node.next
        p.next = n
        n.prev = p
    
    async def build_object(self, primary_key, root = None, curr_table=None): # terrible attempt at auto building, should never be used
        if(not curr_table):
            curr_table = self.sqlapi.tables[root]
        kwargs = {}
        for column in curr_table.__table__.columns:
            if(column.primary_key):
                kwargs[column.name] = primary_key
        
        for name, relationship in inspect(curr_table).relationships.items():
            if(not relationship.uselist): # ill deal with lists later, but for this specific case, i probably wont need them
                kwargs[name] = await self.build_object(primary_key, curr_table=relationship.mapper.class_)
        
            
        return curr_table(**kwargs)

    async def commit(self, node):
        primary_key = node.key
        conf = node.val
        # await session.commit()
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        result = await self.queue.add(self.sqlapi.query_obj, [stmt])
        result = result.scalars().first()
        if(result):
            
            cdict = {}
            ndict = {}
            for column in self.table.__table__.columns:
                name = column.name
                cval = getattr(result, name)
                nval = conf[name]
                
                
                cdict[name]  = cval
                ndict[name] = nval
                
                setattr(result, name, nval)
            await self.queue.add(self.sqlapi.session_commit)
            await self.main.all_loggers["database"][0].debug("Changed row with primary key {} in table {} from {} to {}".format(primary_key, self.table_name, cdict, ndict))
                
        else:
            await self.queue.add(self.sqlapi.add_obj, [self.sqlapi.serialize_dict(conf, self.table_name)])
            
            await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table_name, conf))
                
class SqlCacheParent(aobject):
    async def __init__(self, main):
        self.main = main
        self.sqlapi = self.main.sqlapi
        self.session = self.sqlapi.session
        self.caches = {}
        main.caches = self.caches
        
        for table in list(main.sqlapi.tables.values()):
            if(getattr(table, "hidden", None)):
                continue
            
            self.caches[table.__tablename__] = await SqlCache(self.main, table, self, cachelen = table.cachelen)
        
        # conf = {'server_id': 7, 'rivensettings': {'server_id': 7, 'notify': False}, 'prefix': None}
        # row = await self.caches["servers"].get_row(7, "servers", conf)
        # print(row)
        # await self.caches["servers"].get_row(1)
        # await self.caches["servers"].get_row(2) 


MOD = SqlCacheParent
NAME = "sqlcache"

# caching only supports primary key search because search by when youre trying to search using a query the previous cache objects ion the queue are not yet commited so the query will not account those
# so to query you need max uptime on the database
# when youre searching using pkey, there is only one possible occurence, so its easy to handle, you cant make 2 queries for the same pkey and get 2 different results, then i can just cache that pkey and its row and keep querying that
# when searching using a query tho, there can be multiple occurences for a single obj, for example
# i first "select from servers where id == 1234"
# then change "notify" from false to true
# then i query "select from servers where notify == true"
# but the result from the first and second queries might still be in the cache and not committed to the database thus the query will never account those 
# this isnt a problem with pkey querying because youre only pulling in {key:value} format
# but this problem doesnt exist with add-delete databases
# also if you think i didnt try caching queries, i did, theres just insane # of data redundancies, even with read-write database

from os import readlink
from re import L, T
from telnetlib import PRAGMA_HEARTBEAT
from tkinter.tix import Tree
from traceback import print_tb

from urllib3 import Retry
from models import RivenSettings
from utils.misc import aobject
import asyncio
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy

class Node:
    def __init__(self, key, val, pkey=True):
        self.key = key  # key can be primary key
        self.val = val # val can be value
        self.next = None
        self.prev = None
        self.pkey = pkey
        
class ValueHolder:
    def __init__(self, val, pkey, null) -> None:
        self.val  = val
        self.pkey = pkey
        self.null = null
        self.reference_nodes = []
    
class SqlCache(aobject):
    async def __init__(self, main, table, parent) -> None:
        self.main = main
        self.parent = parent
        self.sqlapi = main.sqlapi
        self.lock = self.sqlapi.lock 
        self.session = self.sqlapi.session
        # self.queue = self.sqlapi.queue
        self.table = table
        self.table_name = table.__tablename__
        
        
        for column in table.__table__.columns:
            if(column.primary_key):
                self.primary_key_attr_str = column.name
                self.primary_key_attr = getattr(self.table, column.name) #i think im dumb
        self.cachelen = table.cachelen
        self.cachenulls = table.cache_nulls #bro idfk im too lazy to implement this yet
        self.readonly = table.readonly
        
        self.query_cache = dict()
        self.cache = dict()
        self.head = Node(0, 0) # initialize hidden and and start of linked list
        self.tail = Node(0, 0)
        self.head.next = self.tail # connect head to teal
        self.tail.prev = self.head
    
    async def add_row(self, primary_key, conf):

        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        await self.lock.acquire()
        async with self.session.begin():
            results = await self.session.execute(stmt)
        self.lock.release()
        result  = results.scalars().first()
        
        if(not result):
                obj = await self.sqlapi.serialize_dict(conf, self.table.__tablename__)
                await self.lock.acquire()
                async with self.session.begin():
                    self.session.add(obj)
                self.lock.release()
                
                await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table.__tablename__, conf))
   
    async def add_tree_conf(self, tree_conf, curr_table, edit):
        cache = self.parent.caches[curr_table]
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
                cdict, ndict = await cache.change_row(pkey, conf, pkey=True)
                await self.main.all_loggers["database"][0].debug("Changed row with primary key {} in table {} from {} to {}".format(pkey, table.__tablename__, cdict, ndict))
        else:
            await cache.add_row(pkey, curr_conf)
            
            
        for name, relationship in inspect(table).relationships.items():
            if(name in tree_conf.keys()):
                attr = tree_conf[name]
                tablename = relationship.target.name
                
                # print(dir(relationship))
                if(isinstance(attr, list)):
                    for _attr in attr:
                        await self.add_tree_conf(_attr, tablename, edit=edit)
                else:
                    await self.add_tree_conf(attr, tablename, edit=edit)
                        
            # print(name, relationship)
        
        
        
    async def get_row(self, primary_key, conf = None, root = None, edit_non_root = False,cache = True):
        await self.main.all_loggers["database"][0].debug("Requested from table {} for primary key {}, cache = {}, conf = {}, root = {}, edit_non_root = {}".format(self.table_name, primary_key, cache, conf, root, edit_non_root))
        # root indicates the starting table containing the primary key linking it to other tables in case a new one needs to be created
        
        if(isinstance(primary_key, sqlalchemy.sql.Select)):
            if(not self.readonly):
                raise Exception("Attempt at querieng objects in non-readonly table {}".format(self.table_name))
            stmt = primary_key
            primary_key = stmt.compile(compile_kwargs={"literal_binds": True}).string
            single_res = False
        else:
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
            single_res = True
            
            
        if(self.cachelen == 0):
            cache = False
        if( cache):
            if(single_res):
                if(primary_key in self.cache.keys()):
                    print("out of el")
                    valholder = self.cache[primary_key]
                    for node in valholder.reference_nodes:
                        await self.remove(node)
                        await self.add(node)
                    return self.cache[primary_key].val
                
                # await self.remove(node)
                # await self.add(node)
            else:
                if(primary_key in self.query_cache.keys()):
                    for valholder in self.query_cache[primary_key]: # <<< This is so data redundant but i have less than 4 braincells to think about this
                        for node in valholder.reference_nodes:
                            await self.remove(node)
                            await self.add(node)
                            
                    print("out of pl")
                    return map(lambda x: x.val, self.query_cache[primary_key])
                
        
        await self.lock.acquire()
        async with self.session.begin():
            results = await self.session.execute(stmt)
        self.lock.release()

        result  = results.scalars().all()
        
        if(not result):
            if(not single_res):
                # IMPLEMENT CACHE NULLS HERE
                if not self.cachenulls: return None
                
            # only single res out from here
            if(conf is None):
                # IMPLEMENT CACHE NULLS HERE
                if not self.cachenulls: return None
            
            if(root is None):
                obj = await self.sqlapi.serialize_dict(conf, self.table.__tablename__)
                await self.lock.acquire()
                async with self.session.begin():
                    self.session.add(obj) # immediately add the obj because we dont want failing dependencies from other tables, theres probably a better way to deal with this but im lazy
                self.lock.release()
                
                await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table.__tablename__, conf))
                result = await self.get_row(primary_key, cache=cache)
                # It isnt worth calculating table from object, if given a complex root, calculation cost is much more expensive than just querying once
                return result
            else:
                
                await self.add_tree_conf(conf, root, edit = edit_non_root)
                result = await self.get_row(primary_key, cache=cache)
                return result
            return
            

        if(single_res):
            result = result[0]
            conf  = await self.sqlapi.deserialize_object(result)
            if(cache):
                value = ValueHolder(conf, primary_key, False)
                
                while (len(self.cache) + len(self.query_cache)) >= self.cachelen:
                    node = self.head.next
                    await self.commit(node)
                    await self.remove(node)
                    if(node.pkey):
                        del self.cache[node.key]
                    else:
                        del self.query_cache[node.key]
                

                self.cache[primary_key] = value
                node = Node(primary_key, value)
                value.reference_nodes.append(node)
                await self.add(node)
                
            return conf
        else:
            results = result
            values = []
            ret = []
            append_to_cache = []
            node = Node(primary_key, values, pkey=False)
            for result in results:
                pkey = getattr(result, self.primary_key_attr_str)
                if(pkey in self.cache.keys()):
                    val = self.cache[pkey]
                    
                    values.append(val)
                    val.reference_nodes.append(node)
                    ret.append(val.val)
                    
                else:
                    conf  = await self.sqlapi.deserialize_object(result)
                    if(cache):
                        val = ValueHolder(conf, pkey, False)
                        values.append(val)
                        append_to_cache.append(val)
                        val.reference_nodes.append(node)
                    ret.append(conf)
            if(cache and len(append_to_cache) + 1 <= self.cachelen):   
                while (self.cachelen - (len(self.cache) + len(self.query_cache))) < (len(append_to_cache) + 1) :
                    node = self.head.next
                    
                    await self.commit(node)
                    await self.remove(node)
                    if(node.pkey):
                        del self.cache[node.key]
                    else:
                        del self.query_cache[node.key]
                for val in append_to_cache:
                    self.cache[val.pkey] = val
                self.query_cache[node.key] = values
                await self.add(node) 
            
            return ret
                    
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

    async def change_row(self, result, conf, pkey=False):
        if(pkey):
            stmt = select(self.table).where(self.primary_key_attr == result)
            result = await self.session.execute(stmt)
            result = result.scalars().first()
        cdict = {}
        ndict = {}
        for column in self.table.__table__.columns:
            name = column.name
            cval = getattr(result, name)
            nval = conf[name]
            
            cdict[name]  = cval
            ndict[name] = nval
            
            setattr(result, name, nval)
        
        await self.session.commit()
        
        return cdict, ndict
        

    async def commit(self, node):
        primary_key = node.key
        valueholder = node.val
        if(self.readonly):
            if(not node.pkey):
                for val in valueholder.val:
                    val.reference_nodes.remove(node)
                    if(len(val.reference_nodes) == 0):
                        del self.cache[valueholder.pkey]
            else:
                valueholder.reference_nodes.remove(node)
                if(len(valueholder.reference_nodes) == 0):
                    del self.cache[valueholder.pkey]
                    
            return
                    
        
        conf = valueholder.val
        # await session.commit()
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        await self.lock.acquire()
        async with self.session.begin():
            result = await self.session.execute(stmt)
        self.lock.release()
        
        result = result.scalars().first()
        if(result):
            await self.lock.acquire()
            cdict, ndict = await self.change_row(result, conf)
            self.lock.release()
            await self.main.all_loggers["database"][0].debug("Changed row with primary key {} in table {} from {} to {}".format(primary_key, self.table_name, cdict, ndict))
        else:
            await self.lock.acquire()
            async with self.session.begin():
                self.session.add(self.sqlapi.serialize_dict(conf, self.table_name))
            self.lock.release()            
            await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table_name, conf))
    
    async def commit_all(self):
        current = self.head.next
          
        while current is not self.tail:
            await self.remove(current)
            await self.commit(current)
            del self.cache[current.key]
            current = current.next   
            
    
            
            
class SqlCacheParent(aobject):
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
            cache = await SqlCache(self.main, table, self)
            self.caches[table.__tablename__] = cache

            self.main.inject_globals(table.__tablename__, cache)
        
        self.main.inject_globals("get_rows", self.get_rows)
        
        # cache = self.caches["shotgun_rivens"]
        # await cache.get_row("abcd", root="shotgun_rivens", conf={"bid_id": "abcd"})
        # stmt = select(self.caches["shotgun_rivens"].table).where(self.caches["shotgun_rivens"].table.bid_id == "abcd")
        # rows = await self.get_rows(stmt)
        # print(rows)
        
        
        servers = self.caches["servers"]
        rivensettings = self.caches["rivensettings"]
        customcommands = self.caches["customcommands"]
        customcommandsroles = self.caches["customcommandsroles"]
        
        server_id = 1234
        config = {
            "server_id": server_id,
            "customcommandssettings": {
                "server_id": server_id,
                "everyone_addc": True,
                "customcommandsroles": [
                {
                    "role_id": 12345678,
                    "server_id": server_id,
                    "addc": True,
                    "delc": True
                },
                {
                    "role_id": 236677,
                    "server_id": server_id,
                    "addc": True,
                    "delc": True
                }]
            }
        }


        # await customcommandsroles.add_tree_conf(config, "servers", False)
        
        
        # stmt = select(customcommandsroles.table).where(customcommandsroles.table.server_id == 1234)
        # rows = await customcommandsroles.get_row(stmt)
        # print(rows)
        # print(customcommandsroles.query_cache)
        # print(customcommandsroles.cache)
        # rows = await customcommandsroles.get_row(stmt)
        # rows = await customcommandsroles.get_row(236677)
        # row["prefix"] = "$"
        # print(servers.cache)
        # row = await servers.get_row(2345, root="servers", conf={"server_id": 2345} )
        # print(servers.cache)
        # print(row)
        
        # row = await customcommands.get_row("1234_commandb", root="servers", conf={"server_id": 1234, "prefix": "$", "customcommands": [{"command_id": "1234_commandb", "name": "commandb", "text": "some b text", "creator": 4567, "server_id": 1234}] }, edit_non_root=True )
        # print(row)
        
        # row = await customcommands.get_row("1234_commandb", root="servers", conf={"server_id": 1234, "customcommands": [{"command_id": "1234_commandb", "name": "commandb", "text": "some b text", "creator": 2345, "server_id": 1234}] } )
        # row = await self.caches["rivensettings"].get_row(880654721197674588, root="servers", conf={"server_id": 880654721197674588, "rivensettings": {"server_id": 880654721197674588, "notify": True}})
        # stmt = select(self.caches["servers"].table).where(self.caches["servers"].table.server_id == 2)
        # rows = await self.get_rows(stmt)

        
    
    async def get_rows(self, stmt): # by statement - if rows exist then - return and bump them in respective caches
        await self.lock.acquire()
        async with self.session.begin():
            result = await self.session.execute(stmt)
        self.lock.release()
        
        if not result:
            return []
        results = result.scalars()
        
        ret = []
        for result in results:
            cache = self.caches[result.__tablename__]
            conf = await self.sqlapi.deserialize_object(result)
            
            if(cache.cache_enabled):
                attr = cache.primary_key_attr_str
                pkey = getattr(result, attr)

                if(len(cache.cache) >= cache.cachelen):
                    node = cache.head.next
                    await cache.commit(node)
                    await cache.remove(node)
                    del cache.cache[node.key]
                

                cache.cache[pkey] = conf
                node = Node(pkey, conf)
                await cache.add(node)
            
            
            ret.append(conf)
        return ret
            

        
    async def closing_func(self):
        for cache in self.caches.values():
            await cache.commit_all()
        
        

MOD = SqlCacheParent
NAME = "sqlcache"

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

from traceback import print_tb

from urllib3 import Retry
from models import RivenSettings
from utils.misc import aobject
import asyncio
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy

class Node:
    def __init__(self, key, val):
        self.key = key  # key can be primary key
        self.val = val # val can be value
        self.next = None
        self.prev = None
        
        
        
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
    
        
        
    async def get_row(self, primary_key, conf = None, cache = True):
        # root indicates the starting table containing the primary key linking it to other tables in case a new one needs to be created
        if(self.cachelen == 0):
            cache = False
        if( cache):
            if(primary_key in self.cache.keys()):
                await self.llist(primary_key)
                return self.cache[primary_key]
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        
        await self.lock.acquire()
        async with self.session.begin():
            results = await self.session.execute(stmt)
        self.lock.release()

    
        result  = results.scalars().first()
        
        # The problem with this root solution is that i currently do not know a way to compute it to use previously created foreign key dependencies
        # it will instead just always create new dependencies even if older one exists resulting in a foreign key exists collision
        # and even if there is a way to compute that i doubt its more efficient/faster than just querying the db for previous stuff
        # computing previous stuff requires querying the database and just manually doing that will be faster i think
        if(not result):
            if(conf is None):

                return None


            obj = await self.sqlapi.serialize_dict(conf, self.table.__tablename__)
            
            await self.lock.acquire()
            async with self.session.begin():
                self.session.add(obj) # immediately add the obj because we dont want failing dependencies from other tables, theres probably a better way to deal with this but im lazy
            self.lock.release()
            
            await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table.__tablename__, conf))
            result = await self.get_row(primary_key, cache=cache)

            # It isnt worth calculating table from object, if given a complex root, calculation cost is much more expensive than just querying once
            return result
        
        
        conf  = await self.sqlapi.deserialize_object(result)
        if(cache):
            if(len(self.cache) >= self.cachelen):
                node = self.head.next
                await self.commit(node)
                await self.remove(node)
                del self.cache[node.key]
            

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

    async def commit(self, node):
        primary_key = node.key
        conf = node.val
        # await session.commit()
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        await self.lock.acquire()
        async with self.session.begin():
            result = await self.session.execute(stmt)
        self.lock.release()
        
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
            await self.lock.acquire()
            await self.session.commit()
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
        # row = await servers.get_row(1234, root="servers", conf={"server_id": 1234, "customcommands": [{"command_id": "1234_commanda", "name": "commanda", "text": "some a text", "creator": 2345, "server_id": 1234}] } )
        
        
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
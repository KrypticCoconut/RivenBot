
from utils.misc import aobject
import asyncio
from sqlalchemy.future import select

class Node:
    def __init__(self, key, val):
        self.key = key  # key can be primary key
        self.val = val # val can be value
        self.next = None
        self.prev = None
        
        
        
class SqlCache(aobject):
    async def __init__(self, main, table, cachelen=20) -> None:
        self.main = main
        self.sqlapi = main.sqlapi
        self.session = self.sqlapi.session
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

    async def get_row(self, primary_key: int):
        if(primary_key in self.cache.keys()):
            await self.llist(primary_key)
            return
        
        stmt = select(self.table).where(self.primary_key_attr == primary_key)
        async with self.session.begin(): #this retarded
            results = await self.session.execute(stmt)
        result  = results.scalars().first()
        if(not result):
            return None
        
        if(len(self.cache) >= self.cachelen):
            node = self.head.next
            await self.commit(node)
            await self.remove(node)
            del self.cache[node.key]
        
        conf  = await self.sqlapi.deserialize_object(result)
        self.cache[primary_key] = conf
        node = Node(primary_key, conf)
        await self.add(node)
        
    async def llist(self, primary_key):
        current = self.head
          
        while True:
              
            if current.key == primary_key:
                node = current
                await self.remove(node)
                print(self.cache)
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
        session = self.session
        primary_key = node.key
        conf = node.val
        # await session.commit()
        async with session.begin():
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
            result = await session.execute(stmt)
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
                
                await self.main.all_loggers["database"][0].debug("Change row with primary key {} in table {} from {} to {}".format(primary_key, self.table_name, cdict, ndict))
                    
            else:
                session.add(self.sqlapi.serialize_dict(conf, self.table_name))
                await self.main.all_loggers["database"][0].debug("Added row with primary key {} in table {} - {}".format(primary_key, self.table_name, conf))
                
class SqlCacheParent(aobject):
    async def __init__(self, main):
        self.main = main
        self.sqlapi = self.main.sqlapi
        self.session = self.sqlapi.session
        self.caches = {}
        
        for table in list(main.sqlapi.tables.values()):
            self.caches[table.__tablename__] = await SqlCache(self.main, table, cachelen=2)
            
        # await self.caches["servers"].get_row(1)
        # await self.caches["servers"].get_row(2)
        # # self.caches["servers"].cache[1]["prefix"] = "@"
        # print(self.caches["servers"].head.next.val)
        # await self.caches["servers"].get_row(1)
        # print(self.caches["servers"].head.next.val)
        self.main.caches = self.caches

MOD = SqlCacheParent
NAME = "sqlcache"
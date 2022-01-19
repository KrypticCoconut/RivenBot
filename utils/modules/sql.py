from ast import Raise
from operator import mod
import sys
import os
import asyncio
import importlib

from utils.misc import aobject

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import scoped_session, sessionmaker, selectinload, noload


# I dont really know how the discord.py event loop works
# This is just a lazy measure to prevent sqlalchemy session transactios I/O collisions
class Queue(aobject):
    async def __init__(self) -> None:
        self.generator = self._queue()
        await self.generator.asend(None)
        
    async def _queue(self):
        while True:
            func = yield
            res = await func[0](*func[1], **func[2])
            yield res
    
    async def add(self, func, args=[], kwargs={}):
        res = await self.generator.asend((func, args, kwargs))
        
        await self.generator.asend(None)
        return res
        

# Low level wrapper to interact with the sqlalchemy api
# sqlcache should be used instead in actual code
class SqlalchemyAPI(aobject):
    async def __init__(self, main, connector, modelspath, debug=False):
        self.main = main
        self.connectorstr = connector 
        
        if(not os.path.exists(modelspath)):
            raise Exception("{} does not exist".format(modelspath))
        spec = importlib.util.spec_from_file_location("module", modelspath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.models = module.models
        self.base = module.Base
        self.modelspath = modelspath
        self.tables = {}
        self.schemas = {}
        self.queue = await Queue()
        
        for model in self.models:
            table, schema = model
            self.tables[table.__tablename__] = table
            self.schemas[table.__tablename__] = schema()
        
        self.engine = create_async_engine(connector)
        self.session = sessionmaker(self.engine, expire_on_commit=False, class_= AsyncSession)()
        
        if(debug):
            await self.sync_tables()
            
        async def create_random(i):
            server = self.tables["servers"](server_id=i, prefix="!", rivensettings = self.tables["rivensettings"](server_id=i, notify=True))
            data = await self.deserialize_object(server)
            await self.queue.add(self.add_obj, [server])
            # result = await self.queue.add(self.query_obj, [select(self.tables["servers"]).where(self.tables["servers"].server_id == i)])
            # print(result.scalars().first())
        
        for i in range(1,5):
            await create_random(i)
        # stmt = select(self.tables["servers"]).where(self.tables["servers"].server_id == 1)
        # obj = await self.query(stmt, first=True, deserialize=False)
        # data  = await self.deserialize_object(obj)
        # print(obj.rivensettings)
        # obj.rivensettings.notify = False
        # await self.session.commit()
        # print(await self.query(stmt, first=True, deserialize=True))

    async def sync_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.drop_all)
            await conn.run_sync(self.base.metadata.create_all)
        
    async def deserialize_object(self, object): # names are flipped because that makes sense scenario wise
        # object is a row
        tablename = object.__tablename__
        schema = self.schemas[tablename]
        return schema.dump(object)
        
    
    async def serialize_dict(self, dict, schemaname):
        schema = self.schemas[schemaname]
        return schema.load(dict)
    
    
    
    async def session_commit(self):
        await self.session.commit()
    
    async def query_obj(self, stmt):
        async with self.session.begin():
            results = await self.session.execute(stmt)
        return results
    
    async def add_obj(self, object):
        async with self.session.begin():
            if(isinstance(object, list)):
                self.session.add_all(object)
            else:
                self.session.add(object)
    
    async def add(self, obj):
        self.session
        

MOD = SqlalchemyAPI
NAME = "sqlapi"
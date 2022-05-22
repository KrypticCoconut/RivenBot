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


# Low level wrapper to interact with the sqlalchemy api and store abstractly related objects
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
        self.meta = module.meta
        self.modelspath = modelspath
        self.tables = {}
        self.schemas = {}
        self.lock = asyncio.Lock()
        
        for model in self.models:
            table, schema = model
            self.tables[table.name] = table
            self.schemas[table.name] = schema
        
        self.engine = create_async_engine(connector)
        if(debug):
            await self.sync_tables()

    async def sync_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.meta.drop_all)
            await conn.run_sync(self.meta.create_all)
        
    async def deserialize_object(self, object, tablename=None): # names are flipped because that makes sense scenario wise
        # object is a row
        if(not tablename):
            tablename = object.__tablename__
        schema = self.schemas[tablename]
        return schema.dump(object)

        
    async def closing_func(self):
        await self.engine.dispose()
        

MOD = SqlalchemyAPI
NAME = "sqlapi"
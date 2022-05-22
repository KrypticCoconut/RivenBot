
from distutils.command.config import config
from re import L
from sys import prefix
from utils.misc import aobject
import asyncio
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.inspection import inspect
import sqlalchemy
import copy
from sqlalchemy import insert, delete, update

class dict_wrapper:
    def __init__(self, old_dict, cache, main) -> None:
        self.cache = cache
        self.engine = self.cache.engine
        self.pkey_attr = self.cache.primary_key_attr_str
        self.main = main
        self.change_wrapper = self.cache.change_wrapper
        
        self.old_dict = old_dict
        self.curr_dict = copy.deepcopy(old_dict)
        
        
    def __getitem__(self, key):
        return self.curr_dict[key]
    
    def __setitem__(self, key, val):
        self.curr_dict[key] = val
    
    def __delitem__(self, key):
        del self.curr_dict[key]
        
    # we dont want a change -> change_wrapper func because the change function indicates that the state of the row is globally changed but it is only locally changed untill update() is called which is a misleading message
            
    async def update(self):
        await self.cache._update_row(self)
        self.last_commit = self.curr_dict
        
    async def delete(self):
        await self.cache.del_row(self.old_dict[self.pkey_attr])



class NoCache(aobject):
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

        

    # primary conf can be a [pkey] or a [stmt]
    async def get_row(self, primary_key, conf = None, root = None, edit = False, **kwargs):
        
        if(isinstance(primary_key, sqlalchemy.sql.Select)):
            stmt = primary_key
            single_res = False
        else:
            single_res = True
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
    
        async with self.engine.begin() as conn:
            results = await conn.execute(stmt)
        
        results = results.fetchall()
        if(not results):
            if(not single_res):
                return # No messing with stmt based confs
            
            if(not conf):
                return
            
            if(not root):
                result = await self.add_row(conf, check=False)
                return result
            else:
                result = await self.add_tree_conf(conf, root, self.table_name, primary_key, edit=edit)
                return result
        ret = []

        for result in results:
            ret.append(dict_wrapper(await self.sqlapi.deserialize_object(result, tablename=self.table_name), main=self.main, cache=self))
        if(single_res):
            ret = ret[0]
        return ret
    
        
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
            
            
    # result can be a [pkey] or a already fetched result obj
    async def _update_row(self, dict_wrapper):

        async with self.engine.begin() as conn:

            

            cdict = dict_wrapper.old_dict
            ndict = dict_wrapper.curr_dict

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
                if(self.change_wrapper): await self.change_wrapper.update(cdict, ndict)
                    
        
    # primarey_key can be a [stmt] or a [pkey]
    # [stmt] needs to return the objects to be delete if self.change_wrapper exists
    async def del_row(self, primary_key): # returns false if nothing is deleted
        if(isinstance(primary_key, sqlalchemy.sql.Delete)):
            stmt = primary_key
            stmt = stmt.returning(self.table)
            async with self.engine.begin() as conn:
                results = await conn.execute(stmt)

            results = results.fetchall()
            for row in results:
                conf = await self.sqlapi.deserialize_object(row, tablename=self.table_name)
                await self.logger.debug("Deleted row with config {} in table {}".format(conf, self.table_name))
                if(self.change_wrapper): await self.change_wrapper.delete(conf)

        else:
            stmt = delete(self.table).where(self.primary_key_attr == primary_key).returning(self.table)
            async with self.engine.begin() as conn:
                result = await conn.execute(stmt)
            row = result.first()
            conf = await self.sqlapi.deserialize_object(row, tablename=self.table_name)
            await self.logger.debug("Deleted row with config {} in table {}".format(conf, self.table_name))
            if(self.change_wrapper): await self.change_wrapper.delete(conf)
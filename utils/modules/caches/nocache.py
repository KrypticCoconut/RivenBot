
from re import L
from sys import prefix
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
        
    # async def change(self, key, value, update=False):
    #     if(key == self.pkey_attr):
    #         pkey = value
            
    #     old = dict(self) # inneficient af
    #     self[key] = value
        
    #     if(self.change_wrapper): await self.change_wrapper(self.cache, old, self, [key])
        
    #     if(update):
    #         await self.update()

    # we dont want a change -> change_wrapper func because the change function indicates that the state of the row is globally changed but it is only locally changed untill update() is called which is a misleading message
            
    async def update(self):
        await self.cache._update_row(self.last_commit[self.pkey_attr], self, pkey=True)
        self.last_commit = dict(self)
        
    async def delete(self):
        await self.cache.del_row(self.last_commit[self.pkey_attr], prev_conf=self.last_commit)



class NoCache(aobject):
    async def __init__(self, main, table, parent):
        self.main = main
        self.parent = parent
        self.sqlapi = main.sqlapi
        self.lock = self.sqlapi.lock # locks shouldnt be used at this level
        self.session = self.sqlapi.session

        self.table = table
        self.table_name = table.__tablename__

        for column in table.__table__.columns:
            if(column.primary_key):
                self.primary_key_attr_str = column.name
                self.primary_key_attr = getattr(self.table, column.name)        
        
        self.logger = self.main.all_loggers["database"][0]

        self.add_tree_conf = parent.add_tree_conf
        
        self.change_wrapper = main.cache_wrapper_extender.cache_wrappers.get(self.table_name, None)

        

    # primary conf can be a [pkey] or a [stmt]
    async def get_row(self, primary_key, conf = None, root = None, edit = False, **kwargs): # can query using a statement or primary key
        
        if(isinstance(primary_key, sqlalchemy.sql.Select)):
            stmt = primary_key
            single_res = False
        else:
            single_res = True
            stmt = select(self.table).where(self.primary_key_attr == primary_key)
    
        async with self.session.begin():
            results = await self.session.execute(stmt)
        
        results = results.scalars().all()
        if(not results):
            if(not single_res):
                return # No messing with stmt based confs
            
            if(not conf):
                return
            
            if(not root):
                await self.add_conf(conf, check=False)
                result = await self.get_row(primary_key)
                return result
            else:
                await self.add_tree_conf(conf, root, edit=edit)
                result = await self.get_row(primary_key)
                return result
        else:
            ret = []

            for result in results:
                ret.append(dict_wrapper(await self.sqlapi.deserialize_object(result), main=self.main, cache=self))
            if(single_res):
                ret = ret[0]
            return ret
    
        
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
        
        await self.logger.debug("Added row with primary key {} in table {} with conf {}".format(conf[self.primary_key_attr_str], self.table_name, conf))
        
        
        if(self.change_wrapper):
            payload= await self.change_wrapper(None, conf[self.primary_key_attr_str])
            if(payload): await payload(self, {}, conf, [])
            
            
    # result can be a [pkey] or a already fetched result obj
    async def _update_row(self, result, conf, pkey=False): # used to update row in database according to given config, can sometimes be used on a surface level
        if(pkey):
            stmt = select(self.table).where(self.primary_key_attr == result)
            async with self.session.begin():
                result = await self.session.execute(stmt)
            result = result.scalars().first()

        async with self.session.begin():
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
                
                if(self.change_wrapper):
                    payload= await self.change_wrapper(cdict[self.primary_key_attr_str], ndict[self.primary_key_attr_str])
                    if(payload): await payload(self, cdict, ndict, [])
                    
        
    # primarey_key can be a [stmt] or a [pkey]
    # [stmt] needs to return the objects to be delete if self.change_wrapper exists
    async def del_row(self, primary_key, prev_conf=None, check=True): # check just checks for row
        if(isinstance(primary_key, sqlalchemy.sql.Select)):
            if(self.change_wrapper):
                async with self.session.begin():
                    results = await self.session.execute(primary_key)
                results = results.scalars().all()
                
                pkeys = {}
                for result in results:
                    pkeys[getattr(result, self.primary_key_attr_str)] = await self.sqlapi.deserialize_object(result)

                for pkey in pkeys.keys():
                    stmt = delete(self.table).where(self.primary_key_attr == pkey)
                    async with self.session.begin():
                        await self.session.execute(stmt)
                        
                    payload = await self.change_wrapper(primary_key, None)
                    await payload(self, pkeys[pkey], {}, [])
                    await self.logger.debug("Deleted row with primary key {} in table {}".format(pkey, self.table_name))
                return
            else:
                return # select and no change_wrapper is no validito
        
        if(isinstance(primary_key, sqlalchemy.sql.Delete)):
                if(not self.change_wrapper):
                    async with self.session.begin(): 
                        await self.session.execute(primary_key)
                    await self.logger.debug("Deleted rows in table {} by statement {}".format(self.table_name, primary_key.compile(compile_kwargs={"literal_binds": True}).string.replace("\n", "")))
                    return
                else:
                    return # delete and change wrapper is no validito
                
        else: # not a special statement
            if(self.change_wrapper):
                
                payload = await self.change_wrapper(primary_key, None)

                if(payload):
                    if(not prev_conf):
                        stmt = select(self.table).where(self.primary_key_attr == primary_key) #if not prev conf, get it

                        async with self.session.begin():
                            result = await self.session.execute(stmt)
                        result = result.scalars().first()
                        
                        if(result):
                            prev_conf = await self.sqlapi.deserialize_object(result)
                        else:
                            return
                    else:
                        result = None
                        if(check):
                            stmt = select(self.table).where(self.primary_key_attr == primary_key)
                            
                            async with self.session.begin(): # check if row exists
                                results = await self.session.execute(stmt)
                            
                            result = results.scalars().first()
                            if(not result):
                                return
                        
                    
                    stmt = delete(self.table).where(self.primary_key_attr == primary_key)

                    async with self.session.begin():
                        result = await self.session.execute(stmt)
                    await payload(self, prev_conf, {}, [])
                    await self.logger.debug("Deleted row with primary key {} in table {}".format(primary_key, self.table_name))
                    
                    return
                else:
                    pass
        
            if(check):
                stmt = select(self.table).where(self.primary_key_attr == primary_key)
                
                async with self.session.begin(): # check if row exists
                    results = await self.session.execute(stmt)
                
                result = results.scalars().first()
                if(not result):
                    return
            
            
            stmt = delete(self.table).where(self.primary_key_attr == primary_key)

            async with self.session.begin():
                result = await self.session.execute(stmt)
            await self.logger.debug("Deleted row with primary key {} in table {}".format(primary_key, self.table_name))

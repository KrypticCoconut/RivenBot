import asyncio
from curses import wrapper
from unicodedata import name
import discord
from sqlalchemy import insert

class Holder():
    all = {}
    
    @classmethod
    def wrapper(cls, name):
        def good_code(cls):
            Holder.all[name] = cls
            return cls
        return good_code

@Holder.wrapper("users")
class servers:
    def __init__(self, main) -> None:
        self.main = main
        
    async def add(self, after):
        print("{}: {{}} -> {}".format(self.cache.table_name, after))
        
        
    async def update(self, before, after):
        print("{}: {} -> {}".format(self.cache.table_name, before, after))
        # log_path = after["log_id"]

        # if(not log_path):
        #     return
        
        # client = self.main.client
        # channel = client.get_channel(log_path)
        # if(not channel):
        #     await self.main.sqlcache.caches["servers"][after[self.cache.primary_key_attr_str]].change("log_path", None) 
        #     return
        # embed=discord.Embed(title="Cache update", color=discord.Color.greyple(), description = "`{}`: ```{}``` -> ```{}```".format(self.cache.table_name, before, after))
        # await channel.send(embed = embed)

    async def delete(self, before):
        print("{}: {} -> {{}}".format(self.cache.table_name, before))
        

async def return_wrappers(main):
    ret = {}
    for table_name, cls in Holder.all.items():
        
        instance = cls(main)
        ret[table_name] = instance
    return ret            
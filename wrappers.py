import asyncio
from curses import wrapper
import discord

class Holder():
    all = []
    
    @classmethod
    def wrapper(cls, name, needs_main):
        def good_code(method):
            Holder.all.append([name, method, needs_main])
        return good_code

@Holder.wrapper("asasa", True)
async def users_wrapper(main):
    async def confirmer(oldpkey, newpkey):
        async def wrapper(cache, before, after, keys_changed):
            print(before, after)
            await main.all_loggers["changes"][0].debug("{}: {} -> {} {}".format(cache.table_name, before, after, keys_changed))
            log_path = None
            if(after == {}):
                log_path = before["log_id"]
            else:
                log_path = after["log_id"]
            
            if(not log_path):
                return
            
            client = main.client
            channel = client.get_channel(log_path)
            if(not channel):
                await main.sqlcache.caches["servers"][after[cache.primary_key_attr_str]].change("log_path", None) 
                return
            embed=discord.Embed(title="Cache update", color=discord.Color.greyple(), description = "`{}`: ```{}``` -> ```{}```".format(cache.table_name, before, after))
            await channel.send(embed = embed)

        # pkey = None
        
        # if(oldpkey is None):
        #     pkey=newpkey
        # else:
        #     pkey = oldpkey
            
        # main.sqlcache.caches[""]
        return wrapper
    return confirmer

async def return_wrappers(main):
    ret = {}
    for pack in Holder.all:
        table_name, method, needs_main = pack
        
        if(needs_main):
            method = await method(main)
        ret[table_name] = method
    return ret            



            
    async def update(self):
        await self.cache._update_row(self.last_commit[self.pkey_attr], self, pkey=True, change_wrapper=True)
        self.last_commit = dict(self)
        
    async def delete(self):
        await self.cache.del_row(self.last_commit[self.pkey_attr], prev_conf=self.last_commit)
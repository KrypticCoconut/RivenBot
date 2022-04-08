from utils.misc import aobject
import importlib
import os

class Cache_Wrapper_Extender(aobject):
    async def __init__(self, main, wrapper_path=None, funcname=None) -> None:
        
        
        if(not os.path.exists(wrapper_path)):
            raise Exception("{} does not exist".format(wrapper_path))
        spec = importlib.util.spec_from_file_location("module", wrapper_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        attr = getattr(module, funcname, None)
        if(not attr):
            raise Exception("attr {} does not exist in {}".format(funcname, wrapper_path))
        
        d = await attr(main=main)
        
        self.cache_wrappers = d

        
        
        
MOD = Cache_Wrapper_Extender
NAME = "cache_wrapper_extender"
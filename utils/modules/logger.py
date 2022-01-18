# asyncio runtime logger
# cant log anything before load_modules()

import sys
import os
import asyncio

from aiologger import Logger
from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.handlers.files import AsyncFileHandler
from aiologger.formatters.base import Formatter

from utils.misc import aobject
from utils.files import *
class LoggerParent(aobject):
    async def __init__(self, main, log_path=None, logger_payloads=[]) -> None:
        
        self.main = main

        if(not log_path):
            log_path = self.main.pwd

        self.all_loggers = dict()
        self.log_path = log_path
        self.primary = None
        
        main.all_loggers = self.all_loggers
        

        for payload in logger_payloads:
            await self.CreateLogger(*payload)
        
        # only inject pre defined loggers
        for name, logger in self.all_loggers.items():
            
            self.main.inject_globals(name, logger[0])
        
        
        

    async def CreateLogger(self, name: str, logginglevel: str, filename: str, primary:bool = False, Streamhandler: bool = False, Filehandler:bool = True, format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
        args = locals()
        # print(name, logginglevel, filename)
        
        filename = os.path.join(self.main.pwd, filename)
        if([key for key,val in self.all_loggers.items() if key == name]):
            raise Exception("cannot have 2 loggers with same name")
        if([val for key,val in self.all_loggers.items() if val[1] == filename]):
            raise Exception("cannot have 2 loggers with same file")
        formatter = Formatter(format)
        logger = Logger(name=name,level=logginglevel)
        

        if(Streamhandler):
            streamhandler = AsyncStreamHandler(stream=sys.stdout)
            streamhandler.level = logginglevel
            streamhandler.formatter = formatter
            logger.add_handler(streamhandler)

        if(Filehandler):
            filehandler = AsyncFileHandler(os.path.join(self.log_path, filename))
            filehandler.level = logginglevel
            filehandler.formatter = formatter
            logger.add_handler(filehandler)
            
        if(primary and self.primary == None):
            self.primary = logger
            self.main.primary = logger
        if(not self.primary):
            raise Exception("Logger was created before primary was created")
        else:
            await self.primary.debug("Logger created with with args {}".format(args))
            
        if(not os.path.exists(os.path.dirname(filename))):
            create_dir_path(filename)
        self.all_loggers[name] = [logger, filename]
    
        
        
        
MOD = LoggerParent
NAME = "logger"


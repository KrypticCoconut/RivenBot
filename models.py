
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import ForeignKey, Table, Column, Integer, String, MetaData, BigInteger, Boolean
from sqlalchemy.future import select
from sqlalchemy import insert, delete, update
from sqlalchemy.inspection import inspect
from marshmallow import fields, Schema

meta = MetaData()


# ==========================================================================

CustomCommands = Table(
    'customcommands', meta,
    Column('command_id', String(500), primary_key=True, nullable=False),
    Column('name', String(500), nullable=False),
    Column('text', String(2000), nullable=False),
    Column('creator', BigInteger, nullable=False),
    Column('server_id', BigInteger, ForeignKey("customcommandssettings.server_id"), nullable=False)
)
CustomCommands.cachelen = 100    

class CustomCommandsSchema(Schema):
    command_id = fields.String()
    name = fields.String()
    text = fields.String()
    server_id = fields.Int()
    creator = fields.Int()

# ==========================================================================


CustomCommandsSettings = Table(
    'customcommandssettings', meta,
    Column('server_id', BigInteger, ForeignKey("servers.server_id"), nullable=False, primary_key=True),
    Column('everyone_addc', Boolean, nullable=False, default=True)
)
CustomCommandsSettings.cachelen = 100    

class CustomCommandsSettingsSchema(Schema):
    server_id = fields.Int()
    everyone_addc = fields.Boolean()

# ==========================================================================

CustomCommandsRoles = Table(
    'customcommandsroles', meta,
    Column('server_id', BigInteger, ForeignKey("customcommandssettings.server_id"), nullable=False),
    Column('role_id', BigInteger, nullable=False, primary_key=True),
    Column('addc', Boolean, nullable=False, default=False),
    Column('delc', Boolean, nullable=False, default=False)
)
CustomCommandsRoles.cachelen = 0


class CustomCommandsRolesSchema(Schema):
    server_id =  fields.Int()
    role_id = fields.Int()
    addc = fields.Boolean()
    delc = fields.Boolean()

# ==========================================================================    

ModeratorRoles = Table(
    'moderatorroles', meta,
    Column('server_id', BigInteger, ForeignKey("servers.server_id"), nullable=False),
    Column('role_id', BigInteger, nullable=False, primary_key=True)
)
ModeratorRoles.cachelen = 0

class ModeratorRolesSchema(Schema):
    server_id =  fields.Int()
    role_id = fields.Int()

# ==========================================================================    

RivenSettings = Table(
    'rivensettings', meta,
    Column('server_id', BigInteger, ForeignKey("servers.server_id"), primary_key=True, nullable=False),
    Column('notfy', Boolean, nullable=False, default=False)
)
RivenSettings.cachelen = 100

class RivenSettingsSchema(Schema):
    server_id = fields.Int()
    notify = fields.Boolean()

# ==========================================================================

Servers = Table(
    'servers', meta,
    Column('server_id', BigInteger, primary_key=True, nullable=False),
    Column('log_id', BigInteger, nullable=True),
    Column('prefix', String(4), nullable=True, default="!")
)
Servers.cachelen = 100

class ServersSchema(Schema):
    server_id = fields.Int()
    prefix = fields.Str(allow_none=True)
    log_id = fields.Int()

# ==========================================================================



models = [
    [Servers, ServersSchema()],
    [RivenSettings, RivenSettingsSchema()],
    [CustomCommandsSettings, CustomCommandsSettingsSchema()],
    [CustomCommands, CustomCommandsSchema()],
    [CustomCommandsRoles, CustomCommandsRolesSchema()],
    [ModeratorRoles, ModeratorRolesSchema()]
] 

# rivensettings = RivenSettings(notify = False, server_id = 1)
# server = Servers(server_id = 1, rivensettings =rivensettings, prefix="abcde")

# schema = ServersSchema()

# dict =  schema.dump(server)
# print(dict)




# reqlink = "https://api.warframe.market/v1/riven/attributes"
# types = {}
# for attr in requests.get(reqlink).json()["payload"]["attributes"]:
#     name = attr["url_name"]
#     if(attr["search_only"]):
#         continue
    

    
#     if(attr["exclusive_to"] == None):
#         for _type in types:
#             if(name not in types[_type]):
#                 types[_type].append(name)

#     else:
#         for _type in attr["exclusive_to"]:
#             if(_type not in types):
#                 types[_type] = []
                
#         for _type in attr["exclusive_to"]:
#             if(name not in types[_type]):
#                 types[_type].append(name)
            
            
# for weapon_type, valid_attrs in types.items(): # Some stats are broken but its whatever
#     table_attrs = {
#         "__tablename__": weapon_type + "_rivens",
#         "__name__": weapon_type,
#         "cachelen": 0,
#         "cache_nulls": False,
#         "bid_id": Column(VARCHAR(300), primary_key=True, nullable=False, autoincrement=False)
#     }


    
#     for attr in valid_attrs:
#         table_attrs[attr] = Column(Boolean, nullable=False, default=False)
        
#     _Table = type( weapon_type + "_rivens", (Base,), table_attrs)
    
    
#     class _T(): # actual gamer god solution
#         bid_id = fields.String()
#         table = _Table
#     for attr in valid_attrs:
#         setattr(_T, attr, fields.Boolean())
    
#     class _Schema(Schema, _T): # actual gamer god solution
#         @post_load
#         def make_user(self, data, **kwargs):
#             return self.table(**data)
        
#     _schema = _Schema()
#     models.append([_Table, _schema])
    


# ====================================================================================================================================================================
# Testing schemas!
# ====================================================================================================================================================================

# users = Table(
#     'users', meta,
#     Column('name', String, primary_key=True),
#     Column('age', Integer),
# )
# users.cachelen = 0

    
# class UsersSchema(Schema):
#     name = fields.String()
#     age = fields.Int()
    
# blogs = Table(
#     'blogs', meta,
#     Column('title', String, primary_key=True),
#     Column('author_name', String , ForeignKey("users.name")),

# )
# blogs.cachelen = 0



# class BlogsSchema(Schema):
#     title = fields.String()
#     author_name = fields.String()
    
# models = [
#     [users, UsersSchema()],
#     [blogs, BlogsSchema()]
# ]
import re
from sqlalchemy.orm import declarative_base
from sqlalchemy import VARCHAR, Column, null, table
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import BigInteger
from sqlalchemy.orm import relationship, backref
from marshmallow import Schema, fields, post_load
import requests

Base = declarative_base()

from types import MethodType

# Example of a simple relationship model

# class Book(Base):
#     __tablename__ = "books"
#     id = Column(Integer, primary_key=True)
#     title = Column(String(30))
#     author_id = Column(Integer, ForeignKey("authors.id"))
    
# class BookSchema(Schema):

#     id = fields.Int()
#     title = fields.Str()
#     author_id = fields.Int()
    
    
# class Author(Base):
#     __tablename__ = "authors"
#     id = Column(Integer, primary_key=True)
#     name = Column(String(30), nullable=False)
#     books = relationship("Book")
#     def __repr__(self):
#         return "<Author(name={self.name!r})>".format(self=self)

# class AuthorSchema(Schema):

#     id = fields.Int()
#     name = fields.Str()
#     books = fields.List(fields.Nested(BookSchema))

class RivenSettings(Base):
    __tablename__ = "rivensettings"
    cachelen = 100
    cache_nulls = False
    server_id = Column(BigInteger, ForeignKey("servers.server_id"), primary_key=True, nullable=False)
    notify = Column(Boolean, nullable=False, default=False)


class CustomCommands(Base):
    __tablename__ = "customcommands"
    cachelen = 100
    cache_nulls = False
    command_id = Column(VARCHAR(500), primary_key=True, nullable=False) # Please understand my position
    name = Column(VARCHAR(500), nullable=False) # fuck data redundancy
    text = Column(VARCHAR(2000), nullable=False)
    creator = Column(BigInteger, nullable=False) 
    server_id = Column(BigInteger, ForeignKey("servers.server_id"), nullable=False)
    

class Servers(Base):
    __tablename__ = "servers"
    cachelen = 100
    cache_nulls = False
    server_id = Column(BigInteger, primary_key=True, nullable=False)
    prefix = Column(String(4), nullable=True, default="!")
    rivensettings = relationship("RivenSettings", uselist=False, lazy="noload") # use .options(selectinload(Servers.rivensettings)) to load relation
    customcommands = relationship("CustomCommands", uselist=True, lazy="noload")

class CustomCommandsSchema(Schema):
    command_id = fields.String()
    name = fields.String()
    text = fields.String()
    server_id = fields.Int()
    creator = fields.Int()
    
    @post_load
    def make_user(self, data, **kwargs):
        return CustomCommands(**data)

class RivenSettingsSchema(Schema):
    server_id = fields.Int()
    notify = fields.Boolean()
    
    @post_load
    def make_user(self, data, **kwargs):
        return RivenSettings(**data)
    
class ServersSchema(Schema):
    server_id = fields.Int()
    prefix = fields.Str(allow_none=True)
    rivensettings = fields.Nested(RivenSettingsSchema)
    customcommands = fields.List(fields.Nested(CustomCommandsSchema))
    
    @post_load
    def make_user(self, data, **kwargs):
        return Servers(**data)
   
models = [
    [Servers, ServersSchema()],
    [RivenSettings, RivenSettingsSchema()],
    [CustomCommands, CustomCommandsSchema()]
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
    

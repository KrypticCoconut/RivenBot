from sqlalchemy.orm import declarative_base
from sqlalchemy import Column
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship, backref
from marshmallow import Schema, fields, post_load

Base = declarative_base()


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
    server_id = Column(Integer, ForeignKey("servers.server_id"), primary_key=True, nullable=False)
    notify = Column(Boolean)

    
    

class Servers(Base):
    __tablename__ = "servers"
    server_id = Column(Integer, primary_key=True, nullable=False)
    prefix = Column(String(4))
    rivensettings = relationship("RivenSettings", uselist=False, lazy="noload") # use .options(selectinload(Servers.rivensettings)) to load relation
    
    


class RivenSettingsSchema(Schema):
    server_id = fields.Int()
    notify = fields.Boolean()
    
    @post_load
    def make_user(self, data, **kwargs):
        return RivenSettings(**data)
    
class ServersSchema(Schema):
    server_id = fields.Int()
    prefix = fields.Str()
    rivensettings = fields.Nested(RivenSettingsSchema)
    
    @post_load
    def make_user(self, data, **kwargs):
        return Servers(**data)
    
    
models = [
    [Servers, ServersSchema],
    [RivenSettings, RivenSettingsSchema]
]
from sqlalchemy import Column, MetaData, ForeignKey, func
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base

import ckan.model as model

log = __import__('logging').getLogger(__name__)

Base = declarative_base()

class CustomLicense(Base):
    """
    A custom license that can be added by users.
    """
    __tablename__ = 'custom_license'

    id = Column(types.UnicodeText, primary_key=True)
    title = Column(types.UnicodeText)
    url = Column(types.UnicodeText)
    user_id = Column(types.UnicodeText, ForeignKey(model.User.id), nullable=False)
    
    
    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id == id).first()

    def as_dict(self):
        d = {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'user_id': self.user_id
        }
      
        return d

def init_tables():
    Base.metadata.create_all(model.meta.engine)

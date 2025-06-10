from sqlalchemy import Column, MetaData, ForeignKey, func
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

import ckan.model as model
import ckan.model.types as _types
import datetime

log = __import__("logging").getLogger(__name__)

Base = declarative_base()


class CUDCImportConfig(Base):
    """
    An import config from other portals.
    """

    __tablename__ = "cudc_import_config"

    id = Column(types.UnicodeText, primary_key=True, default=_types.make_uuid)
    name = Column(types.UnicodeText)
    code = Column(types.UnicodeText)
    notes = Column(types.UnicodeText)
    # "ckan", "socrata"
    platform = Column(types.UnicodeText)
    # The organization to import into
    owner_org = Column(types.UnicodeText)
    stop_on_error = Column(types.BOOLEAN)

    created_by = Column(types.UnicodeText, ForeignKey(model.User.id), nullable=False)

    other_config = Column(MutableDict.as_mutable(JSONB))
    other_data = Column(MutableDict.as_mutable(JSONB))
    # https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules
    cron_schedule = Column(types.UnicodeText)
    is_running = Column(types.BOOLEAN)

    created_at = Column(types.DateTime, default=datetime.datetime.now)
    updated_at = Column(types.DateTime)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        
    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def delete_by_id(cls, id):
        CUDCImportJob.delete_by_config_id(id)
        model.Session.query(cls).filter(cls.id == id).delete()

    def as_dict(self):
        d = {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
            "code": self.code,
            "platform": self.platform,
            "owner_org": self.owner_org,
            "stop_on_error": self.stop_on_error,
            "created_by": self.created_by,
            "other_config": self.other_config or {},
            "other_data": self.other_data or {},
            "cron_schedule": self.cron_schedule,
            "is_running": self.is_running,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return d

    @classmethod
    def get_all_configs(cls):
        return model.Session.query(cls).order_by(cls.created_at).all()


class CUDCImportJob(Base):
    __tablename__ = "cudc_import_job"

    id = Column(types.UnicodeText, primary_key=True, default=_types.make_uuid)
    import_config_id = Column(
        types.UnicodeText, ForeignKey(CUDCImportConfig.id), nullable=False
    )
    has_warning = Column(types.BOOLEAN)
    has_error = Column(types.BOOLEAN)
    logs = Column(types.UnicodeText)
    other_data = Column(MutableDict.as_mutable(JSONB))
    run_at = Column(types.DateTime, default=datetime.datetime.now)
    finished_at = Column(types.DateTime)
    run_by = Column(types.UnicodeText, ForeignKey(model.User.id))
    is_running = Column(types.BOOLEAN)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def delete_by_config_id(cls, id):
        return model.Session.query(cls).filter(cls.import_config_id == id).delete()
    
    @classmethod
    def delete_by_id(cls, id):
        model.Session.query(cls).filter(cls.id == id).delete()
    
    @classmethod
    def get_by_config_id(cls, id):
        return model.Session.query(cls).filter(cls.import_config_id == id).order_by(cls.run_at).all()
    
    @classmethod
    def get_running_jobs_by_config_id(cls, id):
        return model.Session.query(cls).filter(cls.import_config_id == id).filter(cls.is_running == True).order_by(cls.run_at).all()


    def as_dict(self):
        d = {
            "id": self.id,
            "has_warning": self.has_warning,
            "has_error": self.has_error,
            "import_config_id": self.import_config_id,
            "logs": self.logs,
            "other_data": self.other_data,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "run_by": self.run_by,
        }

        return d

    @classmethod
    def get_by_import_config(cls, import_config_id):
        return (
            model.Session.query(cls)
            .filter(cls.import_config_id == import_config_id)
            .order_by(cls.run_at)
            .all()
        )


def init_startup():
    # On CKAN startup, we need to ensure every CUDCImportConfig.is_running is False
    model.Session.query(CUDCImportConfig) \
        .filter(CUDCImportConfig.is_running == True) \
        .update({CUDCImportConfig.is_running: False}
    )
    model.Session.query(CUDCImportJob) \
        .filter(CUDCImportJob.is_running == True) \
        .update({CUDCImportJob.is_running: False}
    )
    model.Session.commit()


def init_tables():
    # Uncomment the following two lines to clear the tables
    # CUDCImportJob.__table__.drop(model.meta.engine)
    # CUDCImportConfig.__table__.drop(model.meta.engine)
    Base.metadata.create_all(model.meta.engine)

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, types, Table
from sqlalchemy.orm import relationship
from ckan import model
from ckan.model.meta import metadata, Session
from ckan.model.domain_object import DomainObject
from sqlalchemy.ext.declarative import declarative_base
import datetime

import ckan.model.types as _types


log = __import__("logging").getLogger(__name__)

Base = declarative_base()

# Association table for admins
organization_access_request_admins = Table(
    "organization_access_request_admins",
    Base.metadata,
    Column(
        "access_request_id",
        types.UnicodeText,
        ForeignKey("organization_access_request.id"),
    ),
    Column("admin_id", types.UnicodeText, ForeignKey(model.User.id)),
)


class OrganizationAccessRequest(Base):

    __tablename__ = "organization_access_request"

    id = Column(types.UnicodeText, primary_key=True, default=_types.make_uuid)
    notes = Column(types.UnicodeText)
    user_id = Column(types.UnicodeText, ForeignKey(model.User.id), nullable=False)
    organization_id = Column(
        types.UnicodeText, ForeignKey(model.Group.id), nullable=False
    )
    # pending, expired, accepted, rejected
    status = Column(types.UnicodeText, nullable=False, default="pending")

    expires_at = Column(
        types.DateTime,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Define relationships
    admins = relationship(
        model.User,
        secondary=organization_access_request_admins,
        backref="received_organization_access_requests",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    def __init__(self, user_id, organization_id, notes, admins=[], expires_at=None, status="pending"):
        if expires_at is None:
            expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
        self.user_id = user_id
        self.expires_at = expires_at
        self.organization_id = organization_id
        self.notes = notes
        self.admins = admins
        self.status = status

    def __repr__(self):
        return "<OrganizationAccessRequest %r>" % self.id

    @classmethod
    def get(cls, id):
        return Session.query(cls).filter(cls.id == id).first()

    @classmethod
    def delete_by_id(cls, id):
        Session.query(cls).filter(cls.id == id).delete()

    @classmethod
    def prune_expired(cls):
        # TODO: This should be a cron job
        expired_requests = (
            Session.query(cls)
            .filter((cls.status == "pending") | (cls.status == "expired"))
            .filter(cls.expires_at < datetime.datetime.now())
            .all()
        )
        for request in expired_requests:
            Session.delete(request)
        Session.commit()
        
    def get_status(self):
        if self.is_expired():
            return "expired"
        return self.status

    def is_expired(self):
        return self.status == "expired" or (
            self.status == "pending" and self.expires_at < datetime.datetime.now()
        )
        
    def accept(self):
        self.status = "accepted"
        Session.commit()
    
    def reject(self):
        self.status = "rejected"
        Session.commit()

    def as_dict(self):
        d = {
            "id": self.id,
            "notes": self.notes,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "admins": [admin.id for admin in self.admins],
            "status": self.get_status(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return d


def init_tables():
    # Uncomment to clear the tables
    # organization_access_request_admins.drop(model.meta.engine)
    # OrganizationAccessRequest.__table__.drop(model.meta.engine)
    Base.metadata.create_all(model.meta.engine)

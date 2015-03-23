"""Cloudhands database models

The data model for Cloudhands is heavily subclassed using the xxxx concept
from SQLAlchemy.

"""

##############################################################################

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, CHAR, ForeignKey
from sqlalchemy import UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship

Base = declarative_base()

from pyramid.security import Allow

from bcrypt import hashpw, gensalt

class RootFactory(object):
    __acl__ = [ (Allow, 'group:users', 'use'),
                (Allow, 'group:agents', 'use'),
                (Allow, 'group:agents', 'act'),
                (Allow, 'group:adminstrators', 'use'),
                (Allow, 'group:adminstrators', 'act'),
                (Allow, 'group:adminstrators', 'administrate') ]
    def __init__(self, request):
        pass

class Actor(Base):
    """
    An actor is any entity which is permitted to make an action. In the
    context of this system, this could be a user or an agent.
    """
    __tablename__ = 'actor'

    id = Column(Integer, primary_key=True)
    """ The primary key of the actor. Subclassed tables inherit this primary
    key. """

    type = Column("type", String(length=32), nullable=False)
    """ The type of actor, eg. 'User'. Provided by subclassed tables upon entry
    creation. """

    uuid = Column("uuid", CHAR(length=32), nullable=False, unique=True)
    """ A uuid for the actor. """

    handle = Column("handle", String(length=64), nullable=True, unique=True)
    """ A handle for the actor. """

    __mapper_args__ = {
        "polymorphic_identity": "actor",
        "polymorphic_on": type
    }

# Actor is subclassed for each type of actor which can
# effect a state-change in the system.

class Component(Actor):
    __tablename__ = 'component'
    id = Column(Integer, ForeignKey('actor.id'), primary_key=True)

class User(Actor):
    """
    A username record. Additional user details are stored as resources.
    """
    __tablename__ = 'user'
    id = Column(Integer, ForeignKey('actor.id'), primary_key=True)
    name = Column(String)
    username = Column(String)

    __mapper_args__ = {"polymorphic_identity": "user"}

    #def __repr__(self):
    #    return "<User(username='%s')>" % self.username

##############################################################################

class Artifact(Base):
    """
    An artifact is an output of the system, created at the request of a user.
    Examples include a registration or an appliance.
    """
    __tablename__ = 'artifact'

    id = Column(Integer, primary_key=True)
    uuid = Column("uuid", CHAR(length=32), nullable=False)
    name = Column("name", CHAR(length=32), nullable=False)
    type = Column("type", String(length=32), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "artifact",
        "polymorphic_on": type}

# The base class of Artifact is subclassed for each type of artifact which
# can be created at the request of a user.

class Appliance(Artifact):
    __tablename__ = 'appliance'
    id = Column(Integer, ForeignKey('artifact.id'), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "appliance"}


class Registration(Artifact):
    __tablename__ = 'registration'
    id = Column(Integer, ForeignKey('artifact.id'), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "registration"}

class Membership(Artifact):
    __tablename__ = 'membership'
    id = Column(Integer, ForeignKey('artifact.id'), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "membership"}

##############################################################################

class Touch(Base):
    """
    A touch is a single alteration to the system. It is created by linking an
    artifact and an actor to a resource, and then recording a state change
    against them.
    """
    __tablename__ = 'touch'

    id = Column(Integer, primary_key=True)
    """ Primary key. """

    artifact_id = Column(Integer, ForeignKey('artifact.id'))
    """ Artifact associated with the touch. """

    actor_id = Column(Integer, ForeignKey('actor.id'))
    """ The actor (eg. user) associated with the touch. """

    state_id = Column(Integer, ForeignKey('state.id'))
    """ A state associated with the touch. What state is the artifact in? """

    touch_dt = Column(DateTime)
    """ Instant at which the touch occurred. """

##############################################################################

class State(Base):
    """
    The nature of Artifacts is that they take some effort to establish, and
    they change over time. Each artifact table has its own State class so
    that business logic can make transitions and persist state in the database.
    """
    __table_args__ = (UniqueConstraint("fsm", "name"),)
    __tablename__ = "state"

    id = Column(Integer, primary_key=True)
    fsm = Column("fsm", String(length=32), nullable=False)
    name = Column("name", String(length=64), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "state", 'polymorphic_on': fsm}

class ArtifactState(State):
    __tablename__ = "artifactstate"

    id = Column("id", Integer, ForeignKey("state.id"),
                nullable=False, primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "artifactstate"}
    #__table_args__ = (CheckConstraint(State.name in ['Stopped', 'Starting', 'Started',
    #                                           'Boosting', 'Boosted','Deboosting',
    #                                           'Suspending', 'Suspended', 'Stopping']),)

##############################################################################

class Resource(Base):
    """
    This is the base table for all resources in the system.

    Resources can have globally unique `uris` if their identity must
    be maintained across sharded databases.

    Some resources have a `provider`. It is common for some resource values
    to be unique within a provider.

    Concrete classes define their own tables according to SQLAlchemy's
    `joined-table inheritance`_.
    """
    __tablename__ = "resource"

    id = Column("id", Integer(), nullable=False, primary_key=True)
    """Primary key."""

    type = Column("type", String(length=32), nullable=False)
    """
    Indicates which sort of resource this record represents. This value is
    provided by subclassed resource tables such as "credit", "email" etc.
    """

    touch_id = Column("touch_id", Integer, ForeignKey("touch.id"))
    """Touch associated with the resource."""

    touch = relationship("Touch")

    __mapper_args__ = {
        "polymorphic_identity": "resource",
        "polymorphic_on": type}

class Node(Resource):
    """
    Represents a physical server, an instance of a virtual machine (VM),
    root jail, container or other computational resource.
    """
    __tablename__ = "node"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)
    name = Column("name", String(length=64), nullable=False)
    uri = Column("uri", String(length=256), nullable=True, unique=True)

    __mapper_args__ = {"polymorphic_identity": "node"}

class Password(Resource):
    """
    Represents a password, which will be bcrypt'ed for you.
    Do not attempt to set the password after creating the object - regard
    it as immutable.
    """
    __tablename__ = "password"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)
    password = Column("password", String(length=64), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "password"}

    def __init__(self, **kwargs):
        #Crypt it
        kwargs['password'] = hashpw(str(kwargs['password']), gensalt())
        super(self.__class__,self).__init__(**kwargs)

    def check(self, candidate):
        """Checks if a candidate password matches the stored crypt-ed password.
        """
        print("xxx" + str(self.password))
        return str(self.password) == hashpw(str(candidate), str(self.password))

class Credit(Resource):
    """Represents the addition or subtraction of credit from the user's account.
    """

    __tablename__ = "credit"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)
    """ Primary key. """

    credit = Column("credit", Integer, nullable=False)
    """The amount by which we are changing the user's account balance.
    Negative integers represent debits from the account. The integer type used
    to define the credit runs from -2147483648 to +2147483647 when implemented
    in Postgres."""

    __mapper_args__ = {"polymorphic_identity": "credit"}

class Specification(Resource):
    """Represents a given set of configuration options for an artifact.
    """
    __tablename__ = "specification"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)

    cores = Column("cores", Integer, nullable=False)
    """The number of cores which we wish a machine to have."""

    ram = Column("ram", Integer, nullable=False)
    """The amount of RAM which we want allocated to the system."""

    __mapper_args__ = {"polymorphic_identity": "specification"}

class Deboost(Resource):
    """
    """
    __tablename__ = "deboost"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)

    deboost_dt = Column(DateTime)

    __mapper_args__ = {"polymorphic_identity": "deboost"}


class Ownership(Resource):
    """
    Represents a change in ownership of a node.
    """
    __tablename__ = "ownership"

    id = Column("id", Integer, ForeignKey("resource.id"),
                nullable=False, primary_key=True)
    user_id = Column("user_id", Integer, ForeignKey("user.id"),
                nullable=False)

    __mapper_args__ = {"polymorphic_identity": "ownership"}

##############################################################################

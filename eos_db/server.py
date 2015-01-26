"""Cloudhands DB server functions

This file contains functions which either make direct modifications to the 
Cloudhands database, request information from the DB, or bundle a series of
functions which cause a number of DB changes to take effect. 
"""
##############################################################################

from eos_db.models import Artifact, Appliance, Registration, Membership
from eos_db.models import Actor, Component, User, Ownership
from eos_db.models import Touch
from eos_db.models import State
from eos_db.models import Resource, Node, Password, Credit
from eos_db.models import Base, engine

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

##############################################################################

def override_engine(engine_string):
    """Sets the target database to a different location than that specified in
    the server module.
    :param engine_string: A SQLAlchemy server string, eg. 'sqlite://'
    """
    global engine
    engine = create_engine(engine_string, echo=True)

def create_user(type, handle, name, username):
    """Create a new user record. 
    
    """
    Base.metadata.create_all(engine)
    new_user = User(name=name, username=username, uuid=handle, handle=handle)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_user)
    session.commit()
    return new_user.id
    
def create_appliance(uuid):
    """
    
    """
    Base.metadata.create_all(engine)
    new_appliance = Appliance(uuid=uuid)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_appliance)
    session.commit()
    return new_appliance.id

def create_states():
    """
    
    """

def create_node():
    """
    Required for the list_server push
    """
    
def change_node_state(node_id, state_id):
    """
    Required for the list_server push
    """

def list_artifacts_for_user(user_id):
    Session = sessionmaker(bind=engine)
    session = Session()
    #our_servers = session.query(Artifact).filter(Artifact.id==Touch.artifact_id).filter(Touch.id==Ownership.touch_id).filter_by(user_id=user_id)
    servers = session.query(Ownership.user_id, Touch.id, Artifact.id, Artifact.uuid).filter(Touch.id==Ownership.touch_id).filter(Artifact.id==Touch.artifact_id).filter_by(user_id=user_id).all()
    result = {}
    for server in servers:
        result[server[3]] = ({"user_id": server[0],"touch_id": server[1],"artifact_id": server[2]}) 
    return result

def touch_to_add_ownership(artifact_id, user_id):
    touch_id=create_touch(None, artifact_id)
    ownership_id=create_ownership(touch_id, user_id)
    return ownership_id

##############################################################################
    
def touch_to_add_password(actor_id, password):
    touch_id = create_touch(actor_id, None)
    password_id = create_password(touch_id, password)
    return password_id

def touch_to_add_credit(actor_id, credit):
    """Creates a touch and an associated credit resource.
    
    :param actor_id: An existing actor id.
    :param credit: An integer from -2147483648 to +2147483647
    :returns: ID of the new credit resource.
    """
    touch_id = _create_touch(actor_id, None)
    success = _create_credit(touch_id, credit)
    return success

def touch_to_add_node():
    """
    
    """
    
    
def touch_to_pre_provisioned():
    """
    
    """
    
def touch_to_provisioned():
    """
    
    """
    
##############################################################################

def _create_touch(actor_id, artifact_id):
    """Add a touch to the database.
    
    :param actor_id: The actor which is making the touch.
    :param artifact_id: The artifact which is associated with the touch.
    :returns: ID of new touch.
    """
    new_touch = Touch(actor_id=actor_id, artifact_id=artifact_id)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_touch)
    session.commit()
    return new_touch.id

def create_password(touch_id, password):
    new_password = Password(touch_id=touch_id, password=password)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_password)
    session.commit()
    return new_password.id

def create_ownership(touch_id, user_id):
    new_ownership = Ownership(touch_id=touch_id, user_id=user_id)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_ownership)
    session.commit()
    return new_ownership.id

def check_password(actor_id, password):
    Session = sessionmaker(bind=engine)
    session = Session()
    our_password = session.query(Password).filter_by(password=password).filter(Password.touch_id==Touch.
id).filter(Touch.actor_id==actor_id).first()
    if our_password is None:
        return False
    else:
        return True

def _create_credit(touch_id, credit):
    """Creates a credit resource.
    
    :param touch_id: A preexisting touch_id
    :param credit: An integer from -2147483648 to +2147483647.
    :returns: ID of newly created credit resource.
    """
    new_credit = Credit(touch_id=touch_id, credit=credit)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_credit)
    session.commit()
    return new_credit.id

def check_credit(actor_id):
    """Returns the credit currently available to the given actor / user.
    
    :param actor_id: The system id of the user or actor for whom we are \
    requesting credit details.
    :returns: Current credit balance. 
    """
    
    Session = sessionmaker(bind=engine)
    session = Session()
    credit = session.query(func.sum(Credit.credit)).filter(Credit.touch_id==Touch.id).filter(Touch.actor_id==actor_id).scalar()
    return credit

def check_actor_id(actor_id):
    """Checks to ensure an actor exists.
    
    :param actor_id: The actor id which we are checking. 
    :returns: True or False
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    if session.query(Actor).filter(Actor.id==actor_id).count() > 0:
        return True
    else:
        return False

##############################################################################

def setup_states():
    pass
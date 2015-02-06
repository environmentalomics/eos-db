"""Cloudhands DB server functions

This file contains functions which either make direct modifications to the 
Cloudhands database, request information from the DB, or bundle a series of
functions which cause a number of DB changes to take effect. 
"""
##############################################################################

from eos_db.models import Artifact, Appliance, Registration, Membership
from eos_db.models import Actor, Component, User, Ownership
from eos_db.models import Touch
from eos_db.models import State, ArtifactState
from eos_db.models import Resource, Node, Password, Credit
from eos_db.models import Base, engine

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from datetime import datetime

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
    session.close()
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
    session.close()
    return new_appliance.id

def create_artifact_state(state_name):
    """
    """
    new_artifact_state = ArtifactState(name=state_name)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_artifact_state)
    session.commit()
    session.close()
    return new_artifact_state.id

def change_node_state(node_id, state_id):
    """
    
    """

def create_node():
    """
    Required for the list_server push
    """

def list_artifacts_for_user(user_id):
    """Returns a list of dictionaries listing pertinent information about
    user's artifacts.
    
    :param user_id: A valid user id for which we want to list details.
    :returns: List of dictionaries containing pertinent info.
    """
    artifacts = []
    for artifact_id, artifact_name in _list_artifacts_for_user(user_id):
        change_dt = _get_most_recent_change(artifact_id)
        create_dt = _get_artifact_creation_date(artifact_id)
        state = _get_most_recent_artifact_state(artifact_id)
        artifacts.append({"artifact_id": artifact_id,
                          "artifact_uuid": artifact_name,
                          "change_dt": str(change_dt[0])[0:16],
                          "create_dt": str(create_dt[0])[0:16],
                          "state": state[0]
                          })
    return artifacts
    
def list_servers_in_state(state):
    Session = sessionmaker(bind=engine)
    session = Session()
    servers = session.query(Artifact.uuid).filter(Touch.artifact_id==Artifact.id).filter(Touch.state_id==State.id).filter_by(name=state).all()
    result = {}
    for server in servers:
        result[server[3]] = ({"user_id": server[0],"touch_id": server[1],"artifact_id": server[2]})
    session.close() 
    return result

def touch_to_add_ownership(artifact_id, user_id):
    touch_id=create_touch(None, artifact_id, None)
    ownership_id=create_ownership(touch_id, user_id)
    return ownership_id

##############################################################################

def touch_to_start(artifact_id):
    """Creates a touch to move the VM into the "pre-start" status.
    
    :param artifact_id: ID of the VM we want to state-shift.
    :returns: ID of progress reference.
    """
    touch_id = _create_touch(None, artifact_id, 3) # Need to change this
    return touch_id

def touch_to_prestart(artifact_id):
    """Creates a touch to move the VM into the "pre-start" status.
    
    :param artifact_id: ID of the VM we want to state-shift.
    :returns: ID of progress reference.
    """
    touch_id = _create_touch(None, artifact_id, 1) # Need to change this
    return touch_id

def touch_to_stop(artifact_id):
    """Creates a touch to move the VM into the "pre-start" status.
    
    :param artifact_id: ID of the VM we want to state-shift.
    :returns: ID of progress reference.
    """
    touch_id = _create_touch(None, artifact_id, 4) # Need to change this
    return touch_id

def touch_to_prestop(artifact_id):
    """Creates a touch to move the VM into the "pre-stop" status.
    
    :param artifact_id: ID of the VM we want to state-shift.
    :returns: ID of progress reference.
    """
    touch_id = _create_touch(None, artifact_id, 2) # Need to change this
    return touch_id
    
def touch_to_presuspend(vm_id):
    """Creates a touch to move the VM into the "pre-start" status.
    
    :param artifact_id: ID of the VM we want to state-shift.
    :returns: ID of progress reference.
    """
    touch_id = _create_touch(None, artifact_id, 3) # Need to change this
    return touch_id

def check_progress(job_id):
    """Looks for the most recent status value in the in-memory progress table.
    
    :param job_id: VM job ID associated with this progress request.
    :returns: Progress value.
    """
    return 0
    
##############################################################################
    
def touch_to_add_password(actor_id, password):
    touch_id = create_touch(actor_id, None, None)
    password_id = create_password(touch_id, password)
    return password_id

def touch_to_add_credit(actor_id, credit):
    """Creates a touch and an associated credit resource.
    
    :param actor_id: An existing actor id.
    :param credit: An integer from -2147483648 to +2147483647
    :returns: ID of the new credit resource.
    """
    touch_id = _create_touch(actor_id, None, None)
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

def _create_touch(actor_id, artifact_id, state_id):
    """Add a touch to the database.
    
    :param actor_id: The actor which is making the touch.
    :param artifact_id: The artifact which is associated with the touch.
    :returns: ID of new touch.
    """
    new_touch = Touch(actor_id=actor_id, artifact_id=artifact_id, state_id=state_id, touch_dt=str(datetime.now()))
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_touch)
    session.commit()
    new_touch_id = new_touch.id
    session.close()
    return new_touch_id

def create_password(touch_id, password):
    new_password = Password(touch_id=touch_id, password=password)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_password)
    session.commit()
    session.close()
    return new_password.id

def create_ownership(touch_id, user_id):
    new_ownership = Ownership(touch_id=touch_id, user_id=user_id)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(new_ownership)
    session.commit()
    session.close()
    return new_ownership.id

def check_password(actor_id, password):
    Session = sessionmaker(bind=engine)
    session = Session()
    our_password = session.query(Password).filter_by(password=password).filter(Password.touch_id==Touch.
id).filter(Touch.actor_id==actor_id).first()
    session.close()
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
    session.close()
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
    session.close()
    return credit

def check_actor_id(actor_id):
    """Checks to ensure an actor exists.
    
    :param actor_id: The actor id which we are checking. 
    :returns: True or False
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    if session.query(Actor).filter(Actor.id==actor_id).count() > 0:
        session.close()
        return True
    else:
        session.close()
        return False

def check_user_details(user_id):
    """Generates a list of account details for an actor.
    
    :param actor_id: The actor id which we are checking. 
    :returns: Dictionary containing user details
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    our_user = session.query(User).filter_by(id=user_id).first()
    session.close()
    return {'id':our_user.id, 'username': our_user.username, 'name': our_user.name}
            
##############################################################################

def setup_states():
    pass

def check_state(artifact_id):
    pass

##############################################################################

def _list_artifacts_for_user(user_id):
    """Generates a list of artifacts associated with the user_id.
    
    :param user_id: A valid user id.
    :returns: List of tuples as (artifact_id, artifact_name)
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    servers = session.query(Artifact.id, Artifact.uuid) \
                .filter(Artifact.id == Touch.artifact_id) \
                .filter(Touch.id == Ownership.touch_id) \
                .filter(Ownership.user_id == user_id) \
                .distinct(Artifact.id).all()
    session.close()
    return servers

def _get_most_recent_change(artifact_id):
    """Returns the date on which an artifact was most recently changed.
    
    :param artifact_id: A valid artifact id.
    :returns: datetime of most recent change (str)
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    change_dt = session.query(func.max(Touch.touch_dt)).filter(Touch.artifact_id == artifact_id).first()
    session.close()
    return change_dt
    
def _get_artifact_creation_date(artifact_id):
    """Returns the data of the first touch recorded against an artifact.
    
    :param artifact_id: A valid artifact id.
    :returns: timestamp of first touch (str)
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    change_dt = session.query(func.min(Touch.touch_dt)).filter(Touch.artifact_id == artifact_id).first()
    session.close()
    return change_dt

def _get_most_recent_artifact_state(artifact_id):
    """Returns the current state of an artifact.
    
    :param artifact_id: A valid artifact id.
    :returns: current state of artifact (str)
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    state = session.query(ArtifactState.name).filter(Touch.artifact_id == artifact_id).filter(ArtifactState.id == Touch.state_id).filter(Touch.touch_dt != None).order_by(Touch.touch_dt.desc()).first()
    session.close()
    return state
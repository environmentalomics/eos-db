"""Cloudhands DB server functions

This file contains functions which either make direct modifications to the
Cloudhands database, request information from the DB, or bundle a series of
functions which cause a number of DB changes to take effect.
"""

from eos_db.models import Artifact, Appliance, Registration
from eos_db.models import Membership, GroupMembership
from eos_db.models import Actor, Component, User, Ownership
from eos_db.models import Touch
from eos_db.models import State, ArtifactState, Deboost, SessionKey
from eos_db.models import Resource, Node, Password, Credit, Specification
from eos_db.models import Base

DB = None
try:
    from eos_db.settings import DBDetails as DB
except:
    # This bare except statement is legit.
    # If no settings file is supplied, we connect to the database eos_db without
    # a username or password - ie. rely on PostgreSQL ident auth.
    pass

EXTRA_STATES = None
try:
    from eos_db.settings import MachineStates as EXTRA_STATES
except:
    pass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, timedelta

engine = ""  # Assume no default database connection

def choose_engine(enginestring):
    """
    Create a connection to a database. If Postgres is selected, this will
    connect to the database specified in the settings.py file. If SQLite is
    selected, then the system will use an in-memory SQLite database.
    As stated in
    http://docs.sqlalchemy.org/en/latest/core/engines.html#configuring-logging
    one should only use echo=True for blanket debugging.  Use the logger
    settings for sqlalchemy.engine instead.
    """
    global engine

    if enginestring == "PostgreSQL":
        if DB and DB.username:
            # Password auth
            engine = create_engine('postgresql://%s:%s@%s/%s'
                                   % (DB.username,
                                      DB.password,
                                      DB.host,
                                      DB.database),
                                   echo=False)
        elif DB:
            engine = create_engine('postgresql:///%s'
                                   % (DB.database),
                                   echo=False)
        else:
            engine = create_engine('postgresql:///eos_db', echo=False)

    elif enginestring == "SQLite":
        engine = create_engine('sqlite://', echo=False)

    else:
        raise LookupError("Invalid server type.")

def override_engine(engine_string):
    """Sets the target database to a different location than that specified in
    the server module.
    :param engine_string: A SQLAlchemy server string, eg. 'sqlite://'
    """
    global engine
    engine = create_engine(engine_string, echo=True)

def deploy_tables():
    """Create tables in their current state in the currently connected
    database.
    """
    Base.metadata.create_all(engine)

def get_state_list():
    """The state list is a union of the internal states we need to function
       plus anything else in EXTRA_STATES
    """
    state_list = (
            'Started',
            'Stopped',
            'Restarting',
            'Starting',
            'Starting_Boosted',
            'Stopping',
            'Preparing',
            'Prepared',
            'Pre_Deboosting',
            'Pre_Deboosted',
            'Deboosted',
            )

    if EXTRA_STATES:
        return state_list + tuple(EXTRA_STATES.state_list)
    else:
        return state_list


def setup_states():
    """ Write the list of valid states to the database. """
    # Make sure states must be distinct
    sdict = {}
    for state in get_state_list:
        if state not in sdict:
            create_artifact_state(state)
            sdict[state] = 1

def create_user(type, handle, name, username):
    """Create a new user record. """
    Base.metadata.create_all(engine)
    user_id = _create_thingy(User(name=name, username=username, uuid=handle, handle=handle))

    #Add this user to a group
    if type:
        create_group_membership(_create_touch(user_id, None, None), type)

    return user_id

def touch_to_add_user_group(username, group):
    """ Adds a touch to the database, then links it to a new user group
        record.
    """
    user_id = get_user_id_from_name(username)
    touch_id = _create_touch(user_id, None, None)
    create_group_membership(touch_id, group)
    return touch_id

def create_group_membership(touch_id, group):
    """ Create a new group membership resource. """
    # FIXME - touch_id was unused, so clearly this was broken.  Needs testing!!!
    # FIXME2 - this is only ever used by the function above so fold the code in.
    Base.metadata.create_all(engine)
    return _create_thingy(GroupMembership(group=group))
    #return _create_thingy(GroupMembership(group=group, touch_id=touch_id))

def get_user_group(username):
    """ Get the group associated with a given username. """
    if username is not None:
        actor_id = get_user_id_from_name(username)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        group = (session
                 .query(GroupMembership.group)
                 .filter(Touch.actor_id == actor_id)
                 .order_by(Touch.touch_dt.desc())
                 .first())
        session.close()
        return group
    else:
        return None


def create_appliance(name, uuid):
    """ Create a new VApp """  # FIXME: We shoehorn VMs into the Vapp record.
    # VMs should go into the "Node" object.
    Base.metadata.create_all(engine)
    return _create_thingy(Appliance(uuid=uuid, name=name))

def create_artifact_state(state_name):
    """ Create a new artifact state. ArtifactState subclasses State. See the
    relevant docs in the model. """
    return _create_thingy(ArtifactState(name=state_name))

def _create_thingy(sql_entity):
    """Internal call that holds the boilerplate for putting a new SQLAlchemy object
       into the database.  BC suggested this should be a decorator but I don't think
       that aids legibility.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(sql_entity)
    session.commit()
    session.close()
    return sql_entity.id


def change_node_state(node_id, state_id):
    """
    Unused.
    """
    pass  # FIXME: See above for comments related to Vapps and VMs.

def create_node():
    """
    Unused.
    """
    pass  # FIXME: See above for comments related to Vapps and VMs.

def list_artifacts_for_user(user_id):
    """Returns a list of dictionaries listing pertinent information about
    user's artifacts.

    :param user_id: A valid user id for which we want to list details.
    :returns: List of dictionaries containing pertinent info.
    """
    artifacts = []
    for (artifact_id,
         artifact_uuid,
         artifact_name) in _list_artifacts_for_user(user_id):
        artifacts.append(return_artifact_details(artifact_id,
                                                 artifact_name,
                                                 artifact_uuid))
    return artifacts

def return_artifact_details(artifact_id, artifact_name="", artifact_uuid=""):
    """ Return basic information about each server. """
    change_dt = _get_most_recent_change(artifact_id)
    create_dt = _get_artifact_creation_date(artifact_id)
    state = _get_most_recent_artifact_state(artifact_id)
    boosted = _get_server_boost_status(artifact_id)
    try:
        boostremaining = get_hours_until_deboost(artifact_id)
        if boostremaining < 0:
            boostremaining = "N/A"
    except:
        boostremaining = "N/A"
    try:
        cores, ram = get_latest_specification(artifact_id)
        ram = str(ram) + " GB"
    except:
        cores, ram = "N/A", "N/A"
    if state == None:
        state = "Not yet initialised"
    else:
        state = state[0]
    if artifact_uuid == "":
        artifact_uuid = get_server_uuid_by_id(artifact_id)[0]
    if artifact_name == "":
        artifact_name = get_server_name_from_id(artifact_id)[0]
    return({"artifact_id": artifact_id,
            "artifact_uuid": artifact_uuid,
            "artifact_name": artifact_name,
            "change_dt": str(change_dt[0])[0:16],
            "create_dt": str(create_dt[0])[0:16],
            "state": state,
            "boosted": boosted,
            "cores": cores,
            "ram": ram,
            "boostremaining": boostremaining
            })

def set_deboost(hours, touch_id):
    """ Set and number of hours in the future at which a VM ought to be
    deboosted. Requires application of an associated touch in order to
    link it to an artifact. """
    deboost_dt = datetime.now()
    deboost_dt += timedelta(hours=hours)
    new_deboost = Deboost(deboost_dt=deboost_dt, touch_id=touch_id)

    return _create_thingy(new_deboost)

def list_servers_in_state(state):
    """ Return a list of servers in the state specified. """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    servers = (session
               .query(Artifact.uuid)
               .filter(Touch.artifact_id == Artifact.id)
               .filter(Touch.state_id == State.id)
               .filter_by(name=state).all())
    result = {}
    for server in servers:
        result[server[3]] = ({"user_id": server[0],
                              "touch_id": server[1],
                              "artifact_id": server[2]})
    session.close()
    return result

def get_server_name_from_id(artifact_id):
    """ Get the name field from an artifact.

    :param artifact_id: A valid artifact id.
    :returns: name of artifact.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    artifact_name = (session
                     .query(Artifact.name)
                     .filter(Artifact.id == artifact_id)
                     .first())
    session.close()
    return artifact_name

def get_server_id_from_name(name):
    """ Get the system ID of a server from its name.

    :param name: The name of an artifact.
    :returns: Internal ID of artifact.
    """
    # FIXME - Check behaviour on duplicate names. This should not be a problem
    # due to database constraints, but is worth looking at, just in case.
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    artifact_id = (session
                   .query(Artifact.id)
                   .filter(Artifact.uuid == name)
                   .first())[0]
    session.close()
    return artifact_id

def get_user_id_from_name(name):
    """ Get the system ID of a user from his name.

    :param name: The name of a user.
    :returns: Internal ID of user.
    """
    # FIXME - Behaviour with duplicates also applies here. Ensure constraints
    # properly set.
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    print (name)
    user_id = session.query(User.id).filter(User.handle == name).first()[0]
    session.close()
    return user_id

def _get_server_boost_status(artifact_id):
    """ Return the boost status (either "Boosted" or "Unboosted" of the given
    artifact by ID.

    Get the system ID of a user from his name.

    :param artifact_id: The artifact in question by ID.
    :returns: String giving boost status.
    """
    # FIXME: Ideally this should really return a boolean to indicate whether a
    # machine is boosted or not.
    try:
        cores, ram = get_latest_specification(artifact_id)
    except:
        cores, ram = 0, 0
    session.close()
    if ram >= 40:
        return "Boosted"
    else:
        return "Unboosted"

def get_deboost_credits(artifact_id):
    """ Get the number of credits which should be refunded upon deboost.

    :param artifact_id: The artifact in question by ID.
    :returns: Number of credits to be refunded..
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    hours = get_hours_until_deboost(artifact_id)
    cores, ram = get_latest_specification(artifact_id)
    multiplier = 0
    if ram == 40:
        multiplier = 1
    if ram == 140:
        multiplier = 3
    if ram == 500:
        multiplier = 12
    return multiplier * hours

    session.close()
    return deboost_credits

def list_server_in_state(state):
    """ Iterates through servers until it finds a server in the state
    requested.

    :param state: A string containing the name of a state.
    :returns: Artifact ID.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    servers = session.query(Artifact.id).all()
    stated_server = None
    for server in servers:
        if _get_most_recent_artifact_state(server[0])[0] == state:
            stated_server = server[0]
    session.close()
    return stated_server

def touch_to_add_ownership(artifact_id, user_id):
    """ Adds an ownership resource to an artifact, effectively linking the VM
    to the user specified. This is in order to prevent users from seeing each
    other's VMs.

    :param artifact_id: The artifact in question by ID.
    :param user_id: The user in question by ID.
    :returns: ownership_id: The ID of the ownership created.
    """
    touch_id = _create_touch(None, artifact_id, None)
    ownership_id = create_ownership(touch_id, user_id)
    return ownership_id

def get_server_uuid_by_id(id):
    """ Get the uuid field from an artifact.

    :param artifact_id: A valid artifact id.
    :returns: uuid of artifact.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    server = session.query(Artifact.uuid).filter(Artifact.id == id).first()
    session.close()
    return server

def check_token(token, artifact_id):
    # FIXME - This was built for the old auth philosophy and has to be altered.
    # It's called only once in views.py
    """Check if artifact belongs to owner of token"""
    # token_actor_id = get_token_owner(token)
    # return check_ownership(artifact_id, token_actor_id)
    return True

def check_ownership(artifact_id, actor_id):
    """ Check if an artifact belongs to a given user.

    :param artifact_id: A valid artifact id.
    :param actor_id: A valid actor id.
    :returns: boolean to indicate ownership.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    our_ownership = (session
                     .query(Ownership)
                     .filter(Ownership.touch_id == Touch.id)
                     .filter(Touch.actor_id == Actor.id)
                     .filter(Actor.handle == actor_id)
                     .order_by(Touch.id.desc())
                     .first())
    session.close()
    if our_ownership is None:
        return False
    else:
        return True


def get_state_id_by_name(name):
    """Gets the id of a state from the name associated with it.

    :param name: A printable state name, as passed to setup_states
    :returns: The corresponding internal state_id
    :raises: IndexError if there is no such state
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    state_id = (session.query(State.id)
                .filter(State.name == name)
                .first())[0]
    session.close()
    return state_id

def touch_to_state(artifact_id, state_name):
    """Creates a touch to move the VM into a given status.
    The state must be a valid state name as passed to setup_states
    - eg. Started, Restarting.

    :param artifact_id: ID of the VM we want to state-shift.
    :param state_name: Target state name, which will be mapped to an ID for us.
    :returns: touch ID
    """
    # Supplying an invalid state will trigger an exception here.
    # Ensure the states were properly loaded in the DB.
    state_id = get_state_id_by_name(state_name)
    touch_id = _create_touch(None, artifact_id, state_id)
    return touch_id

def touch_to_add_deboost(vm_id, hours):
    touch_id = _create_touch(None, vm_id, None)
    set_deboost(hours, touch_id)

def check_and_remove_credits(vm_id, cpu, cores, hours):
    pass

def check_progress(job_id):
    """Looks for the most recent status value in the in-memory progress table.

    :param job_id: VM job ID associated with this progress request.
    :returns: Progress value.
    """
    return 0

def touch_to_add_password(actor_id, password):
    """Sets the password for a user.

    :param actor_id: An existing actor id.
    :param password: The unencrypted password.
    """
    touch_id = _create_touch(actor_id, None, None)
    password_id = _create_thingy(Password(touch_id=touch_id, password=password))

    return password_id

def set_password(username, password):
    """Sets the password for a user by name.  Just a convenience method.
    """
    touch_to_add_password(get_user_id_from_name(username), password)

def touch_to_add_credit(actor_id, credit):
    """Creates a touch and an associated credit resource.

    :param actor_id: An existing actor id.
    :param credit: An integer from -2147483648 to +2147483647
    :returns: ID of the new credit resource.
    """

    touch_id = _create_touch(actor_id, None, None)
    success = _create_credit(touch_id, credit)
    return success

def touch_to_add_specification(vm_id, cores, ram):
    """Creates a touch and associated specification resource.

    :param vm_id: The virtual machine which we want to change.
    :param cores: The number of cores that we want the vm to have.
    :param ram: The amount of RAM, in GB, that we want the vm to have.
    :returns: ID of the new specification resource.
    """
    touch_id = _create_touch(None, vm_id, None)
    success = _create_specification(touch_id, cores, ram)
    return success

def get_latest_specification(vm_id):
    """ Return the most recent / current state of a VM.

    :param vm_id: A valid VM id.
    :returns: String containing current status.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    state = session.query(Specification.cores, Specification.ram). \
        filter(Specification.touch_id == Touch.id). \
        filter(Touch.artifact_id == vm_id). \
        filter(Touch.touch_dt != None). \
        order_by(Touch.touch_dt.desc()).first()
    session.close()
    return state

def get_latest_deboost_dt(vm_id):
    """ Return the most recent / current deboost date of a VM.

    :param vm_id: A valid VM id.
    :returns: String containing most recent deboost date.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    state = session.query(Deboost.deboost_dt). \
        filter(Deboost.touch_id == Touch.id). \
        filter(Touch.artifact_id == vm_id). \
        filter(Touch.touch_dt != None). \
        order_by(Touch.touch_dt.desc()).first()
    session.close()
    return state

def get_hours_until_deboost(vm_id):
    """ Get the number of hours until a VM is due to deboost. """
    now = datetime.now()
    deboost_dt = get_latest_deboost_dt(vm_id)[0]
    d = deboost_dt - now
    return int(d.total_seconds() / 3600)

def get_previous_specification(vm_id, index):
    """
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    state = session.query(Specification.cores, Specification.ram). \
        filter(Specification.touch_id == Touch.id). \
        filter(Touch.artifact_id == vm_id). \
        filter(Touch.touch_dt != None). \
        order_by(Touch.touch_dt.desc()).all()[1]
    session.close()
    return state


def touch_to_add_node():
    """

    """
    # FIXME: Empty, remove

def touch_to_pre_provisioned():
    """

    """
    # FIXME: Empty, remove.

def touch_to_provisioned():
    """

    """
    # FIXME: Empty, remove.

def _create_touch(actor_id, artifact_id, state_id):
    """Add a touch to the database.

    :param actor_id: The actor which is making the touch.
    :param artifact_id: The artifact which is associated with the touch.
    :returns: ID of new touch.
    """
    new_touch = Touch(actor_id=actor_id,
                      artifact_id=artifact_id,
                      state_id=state_id,
                      touch_dt=datetime.now())
    return _create_thingy(new_touch)

def create_ownership(touch_id, user_id):
    """ Add an ownership to a user. This requires a touch to have been created
    linking the artifact to this record. """
    # FIXME: This seems odd - ideally this should just create a touch linking
    # artifact and user, and then add the ownership resource to it. Consider
    # refactoring the ownership mechanism.
    new_ownership = Ownership(touch_id=touch_id, user_id=user_id)
    return _create_thingy(new_ownership)

def check_password(username, password):
    """ Returns a Boolean to describe whether the username and password
    combination is valid. """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    our_password = (session
                    .query(Password)
                    .filter(Password.touch_id == Touch.id)
                    .filter(Touch.actor_id == User.id)
                    .filter(User.username == username)
                    .order_by(Touch.id.desc())
                    .first())
    session.close()
    if our_password is None:
        print ("No password for user")
        return False
    else:
        print ("Checking password" + password)
        return our_password.check(password)

def _create_credit(touch_id, credit):
    """Creates a credit resource.

    :param touch_id: A preexisting touch_id
    :param credit: An integer from -2147483648 to +2147483647.
    :returns: ID of newly created credit resource.
    """
    return _create_thingy(Credit(touch_id=touch_id, credit=credit))

def _create_specification(touch_id, cores, ram):
    """Creates a credit resource.

    :param touch_id: A preexisting touch_id
    :param cores: An integer.
    :param ram: An integer - GB of RAM for machine.
    :returns: ID of newly created specification resource.
    """
    return _create_thingy(Specification(touch_id=touch_id, cores=cores, ram=ram))


def check_credit(actor_id):
    """Returns the credit currently available to the given actor / user.

    :param actor_id: The system id of the user or actor for whom we are \
    requesting credit details.
    :returns: Current credit balance.
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    credit = (session
              .query(func.sum(Credit.credit))
              .filter(Credit.touch_id == Touch.id)
              .filter(Touch.actor_id == Actor.id)
              .filter(Actor.id == actor_id)
              .scalar())
    session.close()
    return credit

def check_actor_id(actor_id):
    """Checks to ensure an actor exists.

    :param actor_id: The actor id which we are checking.
    :returns: True or False
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    if session.query(Actor).filter(Actor.handle == actor_id).count() > 0:
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
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    our_user = session.query(User).filter_by(handle=user_id).first()
    session.close()
    return {'id':our_user.id,
            'username': our_user.username,
            'name': our_user.name
            }

def check_state(artifact_id):
    """ Return None is the artifact has no state assignned to it. Otherwise,
    return the most recent state. """
    state = _get_most_recent_artifact_state(artifact_id)
    if state is None:
        return None
    else:
        return state[0]

def _list_artifacts_for_user(user_id):
    """Generates a list of artifacts associated with the user_id.

    :param user_id: A valid user id.
    :returns: List of tuples as (artifact_id, artifact_name)
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    servers = (session
               .query(Artifact.id, Artifact.uuid, Artifact.name)
               .filter(Artifact.id == Touch.artifact_id)
               .filter(Touch.id == Ownership.touch_id)
               .filter(Ownership.user_id == Actor.id)
               .filter(Actor.handle == user_id)
               .distinct(Artifact.id)
               .all())
    session.close()
    return servers

def _get_most_recent_change(artifact_id):
    """Returns the date on which an artifact was most recently changed.

    :param artifact_id: A valid artifact id.
    :returns: datetime of most recent change (str)
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    change_dt = (session
                 .query(func.max(Touch.touch_dt))
                 .filter(Touch.artifact_id == artifact_id)
                 .first())
    session.close()
    return change_dt

def _get_artifact_creation_date(artifact_id):
    """Returns the data of the first touch recorded against an artifact.

    :param artifact_id: A valid artifact id.
    :returns: timestamp of first touch (str)
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    change_dt = (session
                 .query(func.min(Touch.touch_dt))
                 .filter(Touch.artifact_id == artifact_id)
                 .first())
    session.close()
    return change_dt

def _get_most_recent_artifact_state(artifact_id):
    """Returns the current state of an artifact.

    :param artifact_id: A valid artifact id.
    :returns: current state of artifact (str)
    """
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    state = (session
             .query(ArtifactState.name)
             .filter(Touch.artifact_id == artifact_id)
             .filter(ArtifactState.id == Touch.state_id)
             .filter(Touch.touch_dt != None)
             .order_by(Touch.touch_dt.desc())
             .first())
    session.close()
    return state

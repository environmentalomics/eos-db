"""Cloudhands DB server functions

This file contains functions which either make direct modifications to the
Cloudhands database, request information from the DB, or bundle a series of
functions which cause a number of DB changes to take effect.
"""

from collections import OrderedDict

#We need everything from the models
from eos_db.models import ( Artifact, Appliance, Registration,
                            Membership, GroupMembership,
                            Actor, Component, User, Ownership,
                            Touch, State, ArtifactState, Deboost,
                            Resource, Node, Password, Credit,
                            Specification, Base )

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from copy import deepcopy
from eos_db.json_loader import parse_json_file

engine = None  # Assume no default database connection

# Load config: DB, BL, and EXTRA_STATES
DB = None

# If no Boost Levels are configured supply a baseline default.
# In the case of other exceptions - ie. If the the settings are incomplete -
# let the exception propogate to produce an error.
BL = {}
BL['baseline'] = dict(label='Default', ram=2, cores=1)
BL['levels']   = tuple()
BL['capacity'] = tuple()

EXTRA_STATES = None

def with_session(f):
    """Decorator that automatically passes a Session to a function and then shuts
       the session down at the end, unless a session was already passed through.
       The decorator itself takes no arguments.  The function must have a session
       argument.
    """
    def inner(*args, **kwargs):
        #Note that if session is passed in kwargs the local session
        #variable is never set and therefore is left for the caller to close.
        session = None
        if not kwargs.get('session'):
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            session = Session()
            kwargs['session'] = session
        res = None
        try:
            res = f(*args, **kwargs)
        except Exception as e:
            if session: session.close()
            raise e
        if session:
            session.commit()
            session.close()
        return res
    return inner

def load_config_json(conffile):
    """Loads a specified JSON file and then feeds the configuration from it to
       set_config()
    """
    set_config(parse_json_file(conffile))

def set_config(json_conf):
    """Applies configuration from the supplied dict.
    """

    global DB
    global BL
    global EXTRA_STATES

    if 'DBDetails' in json_conf:
        DB = json_conf['DBDetails']

    if 'BoostLevels' in json_conf:
        BL = json_conf['BoostLevels']

        if 'levels' not in BL:
            BL['levels'] = tuple()
            BL['capacity'] = tuple()

    if 'MachineStates' in json_conf:
        EXTRA_STATES = json_conf['MachineStates']['state_list']
        #It's tempting to call setup_states() here, but we can't initiate the
        #database connection until the DB config is loaded, so it stays on the
        #end of choose_engine()


def choose_engine(enginestring, replace=True):
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

    if engine and not replace:
        return

    if enginestring == "PostgreSQL":
        if DB and DB.get('username'):
            # Password auth
            engine = create_engine('postgresql://%s:%s@%s/%s'
                                   % (DB['username'],
                                      DB['password'],
                                      DB['host'],
                                      DB['database']),
                                   echo=False)
        elif DB:
            engine = create_engine('postgresql:///%s'
                                   % (DB['database']),
                                   echo=False)
        else:
            engine = create_engine('postgresql:///eos_db', echo=False)

    elif enginestring == "SQLite":
        engine = create_engine('sqlite://', echo=False)

    else:
        raise LookupError("Invalid server type.")

    # Always do this.  This bootstraps the database for us, and ensures
    # any new states are added.
    setup_states()


def override_engine(engine_string, echo=True):
    """Sets the target database explicitly to a different location than that
    specified in the server module.
    Note that this doen not deploy the tables - you need to call setup_states()
    or deploy_tables() explicitly afterwards if you want to do that.
    :param engine_string: A SQLAlchemy server string, eg. 'sqlite://'
    """
    global engine
    engine = create_engine(engine_string, echo=echo)

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
            'Boosting',   # Transitional state
            'Deboosting', # Transitional state
            'Error'
            )

    if EXTRA_STATES:
        return state_list + tuple(s for s in EXTRA_STATES if s not in state_list )
    else:
        return state_list


def setup_states(ignore_dupes=True):
    """ Write the list of valid states to the database.
        The states are in server.py and may be supplemented in settings.py.
        With ignore_dupes=False this will throw an exception if you try to
        add the same state twice, otherwise it will just ignore the error - ie.
        it will just add new states and will be idempotent.
    """
    Base.metadata.create_all(engine)
    states_added = 0
    for state in get_state_list():
        try:
            create_artifact_state(state)
            states_added += 1
        except IntegrityError as e:
            if not ignore_dupes: raise e

    return states_added

def get_boost_levels():
    """List the boost levels configured on this server.  If a capacity table has
       been supplied it will also say, for each level, whether it is available.
    """
    if not BL.get('capacity'):
        return(BL)

    #Really?
    bl_copy = deepcopy(BL)

    #Now I need to find the number of machines at each level.  Unfortunately
    #due to the database setup this involves much looping.
    lev_tally = list_servers_by_boost_level()

    #Now I want to see if adding 1 to each value in lev_tally results in a valid
    #capacity row.  Remember that we are always pushing an unboosted machine
    #into a boost state.  I'm going to work from the top level, and as soon
    #as I get a True I'll assume that all lower boosts are also OK.
    #Therefore I'm looking for the top_boost_level
    top_boost_level = -1
    for lev in range(len(lev_tally)-1,-1,-1):
        lev_target = lev_tally.copy()
        lev_target[lev] += 1

        for cap_line in bl_copy['capacity']:
            # What's a neat way to say "all values in lev_target are <= the
            # corresponding value in cap_line"?  Like this...
            if max([ x-y for x, y in zip(lev_target, cap_line)]) <= 0:
                top_boost_level = lev
                break

        if top_boost_level >= 0:
            break

    for lev in range(len(bl_copy['levels'])):
        bl_copy['levels'][lev]['available'] = 1 if lev <= top_boost_level else 0

    return bl_copy

@with_session
def list_user_ids(session):
    """Lists all active user IDs
    """
    #Note that, like for servers, if a new user is created with the same name it
    #overwrites the previous record, so I need to do it like this:
    for n in session.query(User.username).distinct():
        yield get_user_id_from_name(n[0])

def create_user(type, handle, name, username):
    """Create a new user record. Handle/uuid must be unique e-mail address"""
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
    # FIXME?  Should this use the user_id, not username, for consistency?  Not yet sure.
    user_id = get_user_id_from_name(username)
    touch_id = _create_touch(user_id, None, None)
    create_group_membership(touch_id, group)
    return touch_id

def create_group_membership(touch_id, group):
    """ Create a new group membership resource. """
    # FIXME2 - this is only ever used by the function above so fold the code in.
    Base.metadata.create_all(engine)
    #return _create_thingy(GroupMembership(group=group))
    # FIXME (Tim) - touch_id was unused, so clearly this was broken.  Test as-is first.
    return _create_thingy(GroupMembership(group=group, touch_id=touch_id))

@with_session
def get_user_group(username, session):
    """ Get the group associated with a given username. """
    if username is not None:
        actor_id = get_user_id_from_name(username, session=session)
        group = (session
                 .query(GroupMembership.group)
                 .filter(GroupMembership.touch_id == Touch.id)
                 .filter(Touch.actor_id == actor_id)
                 .order_by(Touch.touch_dt.desc())
                 .first())
        #print("get_user_group: User %s is in group %s" % (username, group[0]))
        return group[0]
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

@with_session
def _create_thingy(sql_entity, session):
    """Internal call that holds the boilerplate for putting a new SQLAlchemy object
       into the database.  BC suggested this should be a decorator but I don't think
       that aids legibility.  Maybe should rename this though.
    """
    session.add(sql_entity)
    #Note that this commit causes the .id to be populated.
    session.commit()
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

@with_session
def list_artifacts_for_user(user_id, session):
    """Returns a list of dictionaries listing pertinent information about
    user's artifacts.

    :param user_id: A valid user id for which we want to list details.
    :returns: List of dictionaries containing pertinent info.
    """
    # This bit was  _list_artifacts_for_user(user_id)
    servers = (session
               .query(Artifact.id, Artifact.name, Artifact.uuid)
               .all())

    # Because of my logic that adding a new server with an existing name masks
    # the old server, we actually want to get all the servers here and then
    # post-filter them, or at least that is the simplest approach.

    #OrderedDict gives me the property of updating any server listed
    #twice while still maintaining database order.
    artifacts = OrderedDict()
    for server in servers:
        #Cleanup CHAR values - really should fix this in the DB
        server = list(server)
        server[1] = server[1].rstrip()
        server[2] = server[2].rstrip()
        #END workaround
        if server[1] in artifacts:
            del artifacts[server[1]]
        if check_ownership(server[0], user_id, session=session):
            artifacts[server[1]] = return_artifact_details(*server, session=session)
    return artifacts.values()

@with_session
def return_artifact_details(artifact_id, artifact_name=None, artifact_uuid=None, session=None):
    """ Return basic information about each server, for display.
    """
    change_dt = _get_most_recent_change(artifact_id, session=session)
    create_dt = _get_artifact_creation_date(artifact_id, session=session)
    state = check_state(artifact_id, session=session)
    boosted = _get_server_boost_status(artifact_id)

    boostremaining = "N/A"
    deboost_time = 0
    deboost_credit = 0

    #Because get_time_until_deboost() might report a deboost time for an un-boosted
    #server if it was manually deboosted, check the status
    if boosted:
        time_for_deboost = get_time_until_deboost(artifact_id, session=session)
        boostremaining = time_for_deboost[2] or "Not set"
        # Get deboost time as UNIX seconds-since-epoch
        # Any browser will be able to render this as local time by using:
        #  var d = new Date(0) ;  d.setUTCSeconds(deboost_time)
        deboost_time = time_for_deboost[0].strftime("%s") if time_for_deboost[0] else 0
        deboost_credit = time_for_deboost[3]

    try:
        cores, ram = get_latest_specification(artifact_id, session=session)
        ram = str(ram) + " GB"
    except:
        cores, ram = "N/A", "N/A"
    if state == None:
        state = "Not yet initialised"
    if not artifact_uuid:
        artifact_uuid = get_server_uuid_from_id(artifact_id, session=session)
    if not artifact_name:
        artifact_name = get_server_name_from_id(artifact_id, session=session)

    return({"artifact_id": artifact_id,
            "artifact_uuid": artifact_uuid,
            "artifact_name": artifact_name,
            "change_dt": str(change_dt[0])[0:16],
            "create_dt": str(create_dt[0])[0:16],
            "state": state,
            "boosted": "Boosted" if boosted else "Unboosted",
            "cores": cores,
            "ram": ram,
            "boostremaining": boostremaining,
            "deboost_time": deboost_time,
            "deboost_credit": deboost_credit
            })


#FIXME - rationalise these to three functions:
#  get_server_by_name
#  get_sever_by_id
#  get_server_by_uuid
# That all return the same info as return_artifact_details(id)
@with_session
def get_server_name_from_id(artifact_id, session):
    """ Get the name field from an artifact.

    :param artifact_id: A valid artifact id.
    :returns: name of artifact.
    """
    #For some reason uuid and name have been declared as CHAR in the DB
    #and so they come out space-padded on PostgreSQL.  Strip them here.
    artifact_name = (session
                     .query(Artifact.name)
                     .filter(Artifact.id == artifact_id)
                     .first())
    return artifact_name[0].rstrip()

@with_session
def get_server_id_from_name(name, session):
    """ Get the system ID of a server from its name.

    :param name: The name of an artifact.
    :returns: Internal ID of artifact.
    """
    # FIXME - Check behaviour on duplicate names. This should not be a problem
    # due to database constraints, but is worth looking at, just in case.
    artifact_id = (session
                   .query(Artifact.id)
                   .filter(Artifact.name == name)
                   .order_by(Artifact.id.desc())
                   .first())
    return artifact_id[0]

@with_session
def get_server_id_from_uuid(uuid, session):
    """ Get the system ID of a server from its UUID.

    :param name: The name of an artifact.
    :returns: Internal ID of artifact.
    """
    artifact_id = (session
                   .query(Artifact.id)
                   .filter(Artifact.uuid == uuid)
                   .first())
    return artifact_id[0]

@with_session
def get_user_id_from_name(name, session):
    """ Get the system ID of a user from his name.

    :param name: The username of a user.
    :returns: Internal ID of user.
    """
    # FIXME - Behaviour with duplicates also applies here. Ensure constraints
    # properly set.
    user_id = (session
               .query(User.id)
               .filter(User.username == name)
               .first())
    if not user_id:
        raise KeyError("No such user")
    return user_id[0]

def _get_server_boost_status(artifact_id, session=None):
    """ Return the boost status (either true/"Boosted" or false/"Unboosted") of the given
    artifact by ID.  A VM is believed to be boosted if either the RAM or CPU count is higher
    than the baseline value.

    :param artifact_id: The artifact in question by ID.
    :returns: Bool giving boost status.
    """
    try:
        cores, ram = get_latest_specification(artifact_id, session=session)
    except:
        #New machines must be considered to be like this...
        cores, ram = 0, 0

    return (ram > BL['baseline']['ram']) or (cores > BL['baseline']['cores'])

@with_session
def get_deboost_credits(artifact_id, hours, session):
    """ Get the number of credits which should be refunded upon deboost.
        If you don't know the number of hours call
        get_time_until_deboost(vm_id)[3] instead.

    :param artifact_id: The artifact in question by ID.
    :param hours:  The number of hours to credit.
    :returns: Number of credits to be refunded.
    """

    #Don't end up debiting credits if a deboost is processed late and hours goes negative!
    #Also, this prevents get_latest_specification potentially throwing an exception we
    #don't care about.
    if hours <= 0: return 0

    #This is very similar to the code in check_and_remove_credits but in this case
    #we are less specific.  Find the highest level that the VM meets rather than requiring
    #an exact match.
    cores, ram = get_latest_specification(artifact_id, session=session)
    multiplier = 0
    for lev in BL["levels"]:
        if(cores >= lev['cores'] and ram >= lev['ram']):
            multiplier = lev['cost']

    return multiplier * hours

@with_session
def list_servers_by_state(session):
    """ Iterates through servers and bins them by state.  In a more
        standard database layout we could do this with a single SQL
        query.

    :param state: A string containing the name of a state.
    :returns: Artifact ID.
    """
    servers = session.query(Artifact.name).distinct()
    state_table = {}
    for server_name in servers:
        #Remember that adding a duplicate named server overwrites the old one,
        #so we can't just grab all the server IDs in the table.
        server_id = get_server_id_from_name(server_name[0])

        s_state = check_state(server_id)
        if not s_state:
            #Uninitialised
            pass
        elif s_state in state_table:
            state_table[s_state].append(server_id)
        else:
            state_table[s_state] = [ server_id ]
    return state_table

@with_session
def list_servers_by_boost_level(session):
    """ Iterates through the servers and bins them by boost level.
    """
    # Borrowing code from the function above and from get_deboost_credits
    all_levels =  BL["levels"]
    lev_tally = [0] * len(all_levels)

    servers = session.query(Artifact.name).distinct()
    for server_name in servers:
        #Remember that adding a duplicate named server overwrites the old one,
        #so we can't just grab all the server IDs in the table.
        server_id = get_server_id_from_name(server_name[0])

        try:
            cores, ram = get_latest_specification(server_id, session=session)

            vm_lev = -1
            for i, lev in enumerate(all_levels):
                if(cores >= lev['cores'] and ram >= lev['ram']):
                    vm_lev = i

            if vm_lev >= 0:
                lev_tally[vm_lev] += 1
        except:
            #No worries, we just ignore this machine
            pass

    #That was harder than it could have been, but there you go.
    return lev_tally


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

@with_session
def get_server_uuid_from_id(id, session):
    """ Get the uuid field from an artifact.

    :param artifact_id: A valid artifact id.
    :returns: uuid of artifact.
    """
    #For some reason uuid and name have been declared as CHAR in the DB
    #and so they come out space-padded on PostgreSQL.  Strip them here.
    server = session.query(Artifact.uuid).filter(Artifact.id == id).first()
    return server[0].rstrip()

@with_session
def check_ownership(artifact_id, actor_id, session):
    """ Check if an artifact belongs to a given user.

    :param artifact_id: A valid artifact id.
    :param actor_id: A valid actor (user) id.
    :returns: boolean to indicate ownership.
    """
    our_ownership = (session
                     .query(Ownership)
                     .filter(Ownership.user_id == actor_id)
                     .filter(Ownership.touch_id == Touch.id)
                     .filter(Touch.artifact_id == artifact_id)
                     .order_by(Touch.id.desc())
                     .first())
    if our_ownership is None:
        return False
    else:
        return True

@with_session
def get_state_id_by_name(name, session):
    """Gets the id of a state from the name associated with it.

    :param name: A printable state name, as in get_state_list()
    :returns: The corresponding internal state_id
    :raises: IndexError if there is no such state
    """
    state_id = (session.query(State.id)
                .filter(State.name == name)
                .first())[0]
    return state_id

def touch_to_state(actor_id, artifact_id, state_name):
    """Creates a touch to move the VM into a given status.
    The state must be a valid state name as found in get_state_list()
    - eg. Started, Restarting.

    :param actor_id: User who is initiating the touch.  Can be None.
    :param artifact_id: ID of the VM we want to state-shift.
    :param state_name: Target state name, which will be mapped to an ID for us.
    :returns: touch ID
    """
    # Supplying an invalid state will trigger an exception here.
    # Ensure the states were properly loaded in the DB.
    state_id = get_state_id_by_name(state_name)
    touch_id = _create_touch(actor_id, artifact_id, state_id)
    return touch_id

def touch_to_add_deboost(vm_id, hours):
    """ Set and number of hours in the future at which a VM ought to be
    deboosted. Requires application of an associated touch in order to
    link it to an artifact.
    Note that hours can be fractional even though the user may only boost by the hour.
    This is important for the extend_boost call.
    """
    touch_id = _create_touch(None, vm_id, None)

    deboost_dt = datetime.now()
    deboost_dt += timedelta(hours=hours)
    new_deboost = Deboost(deboost_dt=deboost_dt, touch_id=touch_id)

    return _create_thingy(new_deboost)

def check_and_remove_credits(actor_id, ram, cores, hours):
    """Called when a machine is boosted to see if the user can afford it.
    """

    if actor_id is None:
        #This would happen if an agent called this function.
        #Agents don't get charged.
        return 0

    #This is not ideal - the client requests RAM/Cores explicitly.  We need to see if this
    #translates back to a real boost level and work out the cost.  If there is no exact
    #match we must fail.
    multiplier = -1
    for lev in BL["levels"]:
        if(cores == lev['cores'] and ram == lev['ram']):
            multiplier = lev['cost']

    #Return if we didn't find a match.  Note I'm using -1 as you could conceivably have a free
    #boost level but not one that pays you!
    if multiplier < 0:
        return None

    cost = multiplier * hours

    #See if the user can afford it...
    current_credit = check_credit(actor_id)
    if current_credit >= cost:
        touch_to_add_credit(actor_id, -cost)
        return cost
    else:
        return None

def touch_to_add_password(actor_id, password):
    """Sets the password for a user.

    :param actor_id: An existing actor id.
    :param password: The unencrypted password.
    """
    touch_id = _create_touch(actor_id, None, None)
    password_id = _create_thingy(Password(touch_id=touch_id, password=password))

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

@with_session
def get_latest_specification(vm_id, session):
    """ Return the most recent / current state of a VM.  Equivalent to
        get_previous_specification(index=0) except that this will raise
        an exception if there is no spec in the database.

    :param vm_id: A valid VM id.
    :returns: String containing current status.
    """
    state = ( session
              .query(Specification.cores, Specification.ram)
              .filter(Specification.touch_id == Touch.id)
              .filter(Touch.artifact_id == vm_id)
              .filter(Touch.touch_dt != None)
              .order_by(Touch.touch_dt.desc())
              .first() )
    return state

## Functions that query when a server needs to de-boost.

@with_session
def _get_latest_deboost_dt(vm_id, session):
    """Internal function. Return the most recent / current deboost date of a VM.

    :param vm_id: A valid VM id.
    :returns: String containing most recent deboost date.
    """
    state = ( session
              .query(Deboost.deboost_dt)
              .filter(Deboost.touch_id == Touch.id)
              .filter(Touch.artifact_id == vm_id)
              .filter(Touch.touch_dt != None)
              .order_by(Touch.touch_dt.desc())
              .first() )
    return state

#No with_session decorator actually needed, but a sesh might be passed through.
def get_time_until_deboost(vm_id, session=None):
    """ Get the time until a VM is due to deboost, in various formats.
        We return a quadruplet:
          [ (datetime)deboost_time, (int)secs_until_deboost, (str)display_value, (int)credit ]
    """
    now = datetime.now()
    try:
        deboost_dt = _get_latest_deboost_dt(vm_id,session=session)[0]
        delta = deboost_dt - now
        #Work out what to show the user...
        display_value = None
        if delta.days > 0:
            display_value = "%i days, %02i hrs" % (delta.days, delta.seconds // 3600)
        elif delta.days == 0:
            display_value = "%02i hrs, %02i min" % divmod(delta.seconds // 60, 60)
        else:
            #Too fiddly, and pointless, displaying a negative delta as human-readble.
            #The caller can still look at the first 2 values to inspect expired boosts.
            display_value = "Expired"

        #Work out what any unused time is worth.  This will always be an integer >=0
        credit = get_deboost_credits(vm_id, hours=delta.total_seconds() // 3600)

        return (deboost_dt, int(delta.total_seconds()), display_value, credit)
    except:
        return (None, None, None, 0)


@with_session
def get_deboost_jobs(past, future, session):
    """ Get a list of pending deboosts.  Deboosts scheduled on un-boosted servers
        will always be filtered out here, so there is no need to double-check.
        Note that although you specify the past and future in minutes you get back
        the boost_remain in seconds.
        :param past: How many minutes far back to go.
        :param future : How far forward to look, also in minutes.
        :returns: Array of {server_name, server_id, seconds_remaining}
    """
    now = datetime.now()
    start_time = now - timedelta(minutes=past)
    end_time = now + timedelta(minutes=future)

    deboosts = ( session
                 .query(Deboost.deboost_dt, Touch.artifact_id)
                 .filter(Deboost.deboost_dt > start_time)
                 .filter(Deboost.touch_id == Touch.id)
                 .filter(Touch.touch_dt != None)
                 .order_by(Touch.touch_dt.asc()) )

    #Collect tasks in a dict by server_name, allowing new touches to overwite
    #old ones.
    res = {}

    for d in deboosts:
        server_id = d[1]
        server_name = get_server_name_from_id(server_id)

        # It's possible the touch is attached to a server_id that was overwitten,
        # but then either the real server is un-boosted or else it will have a later
        # deboost set anyway.  But that's why we need the 'del' here...
        if not _get_server_boost_status(server_id):
            if server_name in res : del res[server_name]
            continue

        # If this Deboost if further than end_time minutes away we don't want it,
        # but it will still invalidate any Deboost we already saw.
        if not d[0] <= end_time:
            if server_name in res : del res[server_name]
            continue

        res[server_name] = d

    #And return an array of triples as promised
    return [ dict(artifact_name=n,
                  artifact_id=i[1],
                  boost_remain=int( (i[0] - now).total_seconds() ) )
             for n,i in res.items() ]

@with_session
def get_previous_specification(vm_id, index=1, session=None):
    """Get the previous machine spec, or indeed the last-but-one or whatever
       index you like.  If the index is out of range this will return the default
       baseline spec.
    """
    state = ( session
              .query(Specification.cores, Specification.ram)
              .filter(Specification.touch_id == Touch.id)
              .filter(Touch.artifact_id == vm_id)
              .filter(Touch.touch_dt != None)
              .order_by(Touch.touch_dt.desc())
              .all() )

    try:
        return state[index]
    except IndexError:
        return BL['baseline']['cores'], BL['baseline']['ram']


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

@with_session
def check_password(username, password, session):
    """ Returns a Boolean to describe whether the username and password
    combination is valid. """
    our_password = (session
                    .query(Password)
                    .filter(Password.touch_id == Touch.id)
                    .filter(Touch.actor_id == User.id)
                    .filter(User.username == username)
                    .order_by(Touch.id.desc())
                    .first())
    if our_password is None:
        return False
    else:
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

@with_session
def check_credit(actor_id, session):
    """Returns the credit currently available to the given actor / user.

    :param actor_id: The system id of the user or actor for whom we are \
    requesting credit details.
    :returns: Current credit balance.  If there is no credit record for the \
              user will return zero.
    """
    credit = (session
              .query(func.sum(Credit.credit))
              .filter(Credit.touch_id == Touch.id)
              .filter(Touch.actor_id == Actor.id)
              .filter(Actor.id == actor_id)
              .scalar())
    return credit or 0

@with_session
def check_actor_id(actor_id, session):
    """Checks to ensure an actor exists.

    :param actor_id: The actor id which we are checking.
    :returns: True or False
    """
    return ( session
             .query(Actor)
             .filter(Actor.id == actor_id)
             .count() )

@with_session
def check_user_details(user_id, session):
    """Generates a list of account details for an actor.

    :param user_id: The actor id which we are checking.
    :returns: Dictionary containing user details
    """
    our_user = session.query(User).filter_by(id=user_id).first()
    #TODO - add user group
    return {'id':our_user.id,
            'handle':our_user.handle,
            'username': our_user.username,
            'name': our_user.name
            }

@with_session
def check_state(artifact_id, session):
    """Returns the current state of an artifact, or None if no state
       has been set.

    :param artifact_id: A valid artifact id.
    :returns: current state of artifact (str)
    """
    state = (session
             .query(ArtifactState.name)
             .filter(Touch.artifact_id == artifact_id)
             .filter(ArtifactState.id == Touch.state_id)
             .filter(Touch.touch_dt != None)
             .order_by(Touch.touch_dt.desc())
             .first())
    return state[0] if state else None

@with_session
def _get_most_recent_change(artifact_id, session):
    """Returns the date on which an artifact was most recently changed.

    :param artifact_id: A valid artifact id.
    :returns: datetime of most recent change (str)
    """
    change_dt = (session
                 .query(func.max(Touch.touch_dt))
                 .filter(Touch.artifact_id == artifact_id)
                 .first())
    return change_dt

@with_session
def _get_artifact_creation_date(artifact_id, session):
    """Returns the data of the first touch recorded against an artifact.

    :param artifact_id: A valid artifact id.
    :returns: timestamp of first touch (str)
    """
    change_dt = (session
                 .query(func.min(Touch.touch_dt))
                 .filter(Touch.artifact_id == artifact_id)
                 .first())
    return change_dt

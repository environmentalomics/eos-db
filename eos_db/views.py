"""API functions for controlling the Cloudhands DB

This module contains all the API functions available on the Cloudhands RESTful
API. Modifications requests to the database are mediated through functions in
the "server" module.
"""

import json, uuid
import hashlib, base64, random
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import (HTTPBadRequest, HTTPNotImplemented,
                                    HTTPUnauthorized, HTTPForbidden,
                                    HTTPNotFound, HTTPInternalServerError )
from pyramid.security import Allow, Everyone

from eos_db import server

# Patch for view_config - as we're not calling any of these functions directly it's
# too easy to accidentally give two funtions the same name, and then wonder why
# the result is a 404 error.
# This workaround patches the view_config decorator so that it complains when you
# try to decorate a function that has already been declared.  The behaviour should
# be otherwise unaffected.
# (Note that pyflakes3 is a good way to pick up this issue too.)
# Also, for bonus points, implement the routes=[list] argument.
_view_config = view_config
def view_config(*args, **kwargs):
    def new_decorator(f):
        if f.__name__ in globals():
            raise AttributeError("This module already has a function %s() defined" % f.__name__)
        if 'routes' in kwargs:
            for r in kwargs.pop('routes'):
                f = _view_config(*args, route_name=r, **kwargs)(f)
            return f
        else:
            return _view_config(*args, **kwargs)(f)
    return new_decorator

class PermissionsMap():
    """This is passed to pyramid.config.Configurator in __init__.py,
       and defines the permissions attributed to each group. """

    __acl__ = [(Allow, Everyone,               'login'),
               (Allow, 'group:users',          'use'),
               (Allow, 'group:agents',         'use'),
               (Allow, 'group:agents',         'act'),
               (Allow, 'group:administrators', 'use'),
               (Allow, 'group:administrators', 'act'),
               (Allow, 'group:administrators', 'administer')]
    def __init__(self, request):
        """ No-operations here. """
        pass

@view_config(request_method="GET", route_name='home', renderer='json')
def home_view(request):
    """ Return a list of all valid API calls by way of documentation. """
    call_list = {"Valid API Call List":{
                              "See valid Boost levels": "/boostlevels",
                              "Retrieve User List": "/users",
                              "Get my details": "/user",
                              "Get my touches": "/user/touches",
                              "Set my password": "/user/password",
                              "Get my credit": "/user/credit",
                              "servers": "/servers",  # Return server list
                              "Server details by name": "/servers/{name}",  # Get server details or
                              "Server details by ID": "/servers/by_id/{id}",
                              "Start a server": "/servers/{name}/Starting",
                              "Stop a server": "/servers/{name}/Stopping",
                              "Restart a server": "/servers/{name}/Restarting",
                              "De-Boost a server": "/servers/{name}/pre_deboosting",
                              "server_Pre_Deboosted": "/servers/{name}/Pre_deboosted",
                              "server_Deboost": "/servers/{name}/deboosting",
                              "server_Started": "/servers/{name}/Started",
                              "server_Stopped": "/servers/{name}/Stopped",
                              "Boost a server": "/servers/{name}/preparing",
                              "server_Prepared": "/servers/{name}/prepared",
                              "server_owner": "/servers/{name}/owner",
                              "server_touches": "/servers/{name}/touches",
                              "CPU/RAM Specification": "/servers/{name}/specification",
                              "All states, and count by state": "/states",
                              "Servers is state": "/states/{name}",
                              "Servers needing deboost": "/deboost_jobs",
                              }
                 }
    return call_list

@view_config(request_method="GET", route_name='boostlevels', renderer='json')
def blview(request):
    return server.get_boost_levels()

# OPTIONS call result

@view_config(request_method="OPTIONS", routes=['home', 'servers'])
def options(request):
    """ Return the OPTIONS header. """
    # NOTE: This is important for enabling CORS, although under certain
    # circumstances the browser doesn' appear to need it. Might be worth
    # examining why.
    resp = Response(None)
    resp.headers['Allow'] = "HEAD,GET,OPTIONS"
    return resp

@view_config(request_method="OPTIONS", routes=['server', 'server_specification'])
@view_config(request_method="OPTIONS", routes=['server_by_id', 'server_by_id_specification'])
def options2(request):
    resp = Response(None)
    resp.headers['Allow'] = "HEAD,GET,POST,OPTIONS"
    return resp

@view_config(request_method="OPTIONS", routes=["server_" + x for x in server.get_state_list()])
@view_config(request_method="OPTIONS", routes=["server_by_id_" + x for x in server.get_state_list()])
@view_config(request_method="OPTIONS", routes=['server_extend_boost', 'server_by_id_extend_boost'])
def options3(request):
    resp = Response(None)
    resp.headers['Allow'] = "HEAD,POST,OPTIONS"
    return resp

# End of OPTIONS guff

@view_config(request_method="GET", route_name='users', renderer='json', permission="use")
def retrieve_users(request):
    """Return details for all users on the system.  Basically the same as calling /users/x
       for all users, but missing the credit info.
    """
    res = []
    for user_id in server.list_user_ids():
        res.append(server.check_user_details(user_id))

    return res


@view_config(request_method="PUT", route_name='user', renderer='json', permission="administer")
def create_user(request):
    """ Create a user in the database. """
    #FIXME - the UUID for a user should be the e-mail address.  Can we make this explicit?
    newname = server.create_user(request.POST['type'], request.POST['handle'], request.POST['name'], request.matchdict['name'])
    return newname

@view_config(request_method="GET", route_name='user', renderer='json', permission="use")
def retrieve_user(request):
    """Return account details for any user.  Anybody should be able to do this,
       though most users have no need to.

    :param name: The user we are interested in.
    :returns JSON object containing user table data.
    """
    username = request.matchdict['name']
    try:
        actor_id = server.get_user_id_from_name(username)
        details = server.check_user_details(actor_id)
        details.update({'credits' : server.check_credit(actor_id)})
        return details
    except KeyError:
        return HTTPNotFound()

@view_config(request_method="GET", route_name='my_user', renderer='json', permission="use")
def retrieve_my_user(request):
    """Return account details for logged-in user.

    :param name: The user we are interested in.
    :returns JSON object containing user table data.
    """
    username = request.authenticated_userid
    try:
        actor_id = server.get_user_id_from_name(username)
        details = server.check_user_details(actor_id)
        details.update({'credits' : server.check_credit(actor_id)})
        return details
    except KeyError:
        #Should be impossible unless a logged-in user is deleted.
        return HTTPInternalServerError()

@view_config(request_method="PATCH", route_name='user', renderer='json', permission="administer")
def update_user(request):
    # FIXME: Not implemented.
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='user', renderer='json', permission="administer")
def delete_user(request):
    # FIXME: Not implemented. Some thought needs to go into this. I think a
    # deletion flag would be appropriate, but this will involve changing quite
    # a number of queries.
    # Tim thinks - makbe just lock the password and remove all machines?
    response = HTTPNotImplemented()
    return response

@view_config(request_method="PUT", route_name='user_password', renderer='json', permission="administer")
def create_user_password(request):
    """ Creates a password for the user given. """
    username = request.matchdict['name']
    actor_id = server.get_user_id_from_name(username)
    newname = server.touch_to_add_password(actor_id, request.POST['password'])
    #FIXME - should we not just return OK?
    return newname

@view_config(request_method="PUT", route_name='my_password', renderer='json', permission="use")
def create_my_password(request):
    """ Creates a password for the user given. """
    username = request.authenticated_userid
    actor_id = server.get_user_id_from_name(username)
    newname = server.touch_to_add_password(actor_id, request.POST['password'])
    #FIXME - should we not just return OK?
    #FIXME2 - also should this not be a POST?
    return newname

@view_config(request_method="GET", route_name='user_touches', renderer='json', permission="use")
def retrieve_user_touches(request):
    # FIXME - Not implemented.
    name = request.matchdict['name']
    return name

@view_config(request_method="POST", route_name='user_credit', renderer='json', permission="administer")
def create_user_credit(request):
    """Adds credit to a user account, negative or positive.  Only an administrator can do this
       directly.  Boost and Deboost actions will do this implicitly.

    Checks if username is valid, otherwise throws HTTP 404.
    Checks if credit is an integer, otherwise throws HTTP 400.

    :param name: User for which we are amending credit.
    :returns: JSON containing actor id, credit change and new balance.
    """
    username, credit = request.matchdict['name'], request.POST['credit']
    try:
        user_id = server.get_user_id_from_name(username)
        server.touch_to_add_credit(user_id, int(credit))
        credits = server.check_credit(user_id)
        return  {'actor_id': int(user_id),
                 'credit_change': int(credit),
                 'credit_balance': int(credits)}
    except ValueError:
        return HTTPBadRequest()
    except KeyError:
        return HTTPNotFound()

# Not sure if Ben was in the process of folding credit balance into user details
# or splitting it out.  I vote for folding it in.
# DELETEME
#
# @view_config(request_method="GET", route_name='my_credit', renderer='json', permission="use")
# def retrieve_my_credit(request):
#     """Return credits outstanding for current user.
#
#     :returns: JSON containing actor_id and current balance.
#     """
#     username = request.authenticated_userid
#     actor_id = server.get_user_id_from_name(username)
#     # actor_id should be valid
#     credits = server.check_credit(actor_id)
#     return  { 'actor_id': actor_id,
#               'credit_balance': int(credits)}

# FIXME - should just return credit to match the POST above.
@view_config(request_method="GET", route_name='user_credit', renderer='json', permission="act")
def retrieve_user_credit(request):
    """Return credits outstanding for any user.

    :param name: User for which we are checking credit.
    :returns: JSON containing actor_id and current balance.
    """
    username = request.matchdict['name']
    try:
        user_id = server.get_user_id_from_name(username)
        credits = server.check_credit(user_id)
        return  {'actor_id': user_id,
                 'credit_balance': int(credits)}
    except KeyError as e:
        return HTTPNotFound(str(e))


@view_config(request_method="GET", route_name='servers', renderer='json', permission="use")
def retrieve_servers(request):
    """
    Lists all artifacts related to the current user.
    """
    user_id = None
    try:
        user_id = server.get_user_id_from_name(request.authenticated_userid)
    except:
        pass
        #This should only happen if the user is an agent, right?
    server_list = server.list_artifacts_for_user(user_id)
    return list(server_list)

@view_config(request_method="GET", route_name='states', renderer='json', permission="use")
def retrieve_server_counts_by_state(request):
    """
    List all states and the number of servers in that state.
    """
    #Note that with the current DB schema, having the separate state and states calls is silly
    #because both retrieve the same info from the DB then selectively throw bits away.
    server_table = server.list_servers_by_state()

    all_states = server.get_state_list()

    #Not so good - we'd like to report all valid states...
    #return { k: len(v) for k, v in server_table }

    #Better...
    return { s: len(server_table.get(s, ())) for s in all_states }


@view_config(request_method="GET", route_name='state', renderer='json', permission="use")
def retrieve_servers_in_state(request):
    """
    Lists all servers in a given state.
    """
    server_ids = server.list_servers_by_state().get(request.matchdict['name'],())
    server_uuid = [ server.get_server_uuid_from_id(s_id) for s_id in server_ids ]
    server_name = [ server.get_server_name_from_id(s_id) for s_id in server_ids ]
    return [ { "artifact_id"   : s[0],
               "artifact_uuid" : s[1],
               "artifact_name" : s[2] }
             for s in zip(server_ids, server_uuid, server_name) ]

@view_config(request_method="PUT", route_name='server', renderer='json', permission="administer")
def create_server(request):
    """
    Creates a new artifact record in the database.
    """
    newname = server.create_appliance(request.matchdict['name'], request.POST['uuid'])
    return newname

@view_config(request_method="GET", routes=['server', 'server_by_id'], renderer='json', permission="use")
def retrieve_server(request):
    """
    Gets artifact details from the server, based on the name or the internal ID.
    """
    vm_id, actor_id = _resolve_vm(request)
    server_details = server.return_artifact_details(vm_id)
    return server_details

@view_config(request_method="PATCH", route_name='server', renderer='json', permission="use")
def update_server(request):
    # FIXME: Not implemented. Do we want this to be implemented?
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='server', renderer='json', permission="use")
def delete_server(request):
    # FIXME: Not implemented. Again, this needs thought. Probably logical
    # deletion through a "deleted" flag.
    # Or else, add a new server with the same name and blank UUID, as currently for multiple
    # servers with the same name we only see the last.
    response = HTTPNotImplemented()
    return response

@view_config(request_method="PUT", route_name='server_owner', renderer='json', permission="use")
def create_server_owner(request):
    """ Calls touch_to_add_ownership to add an owner to the server. """
    # FIXME: There is the problem of servers being able to have multiple
    # owners in the current system. Again, we may need a logical deletion
    # flag. On reflection, I'd like to suggest that we add a logical deletion
    # flag to the Resource class, as it'll be inherited by all resources,
    # and solves multiple problems in one place.
    newname = server.touch_to_add_ownership(request.matchdict['name'], request.POST['actor_id'])
    return newname

@view_config(request_method="GET", route_name='server_owner', renderer='json', permission="use")
def get_server_owner(request):
    # Not implemented. Check if necessary.  A server can have many owners.
    return HTTPNotImplemented()

def _resolve_vm(request):
    """Function given a request works out the VM we are talking about and whether
       the current user actually has permission to do stuff to it.
       Also returns the internal ID for the user, as well as the VM.
    """

    actor_id = None
    vm_id = None
    try:
        actor_id = server.get_user_id_from_name(request.authenticated_userid)
    except:
        #OK, it must be an agent or an internal call.
        pass
    try:
        vm_id = ( request.matchdict['id']
                  if 'id' in request.matchdict else
                  server.get_server_id_from_name(request.matchdict['name']) )
    except:
        #Presumably because there is no such VM
        raise HTTPNotFound()

    if ( request.has_permission('act') or
         server.check_ownership(vm_id, actor_id) ):
        return vm_id, actor_id
    else:
        raise HTTPUnauthorized()

@view_config(request_method="GET", routes=['server_state', 'server_by_id_state'],
             renderer='json', permission="use")
def server_state(request):
    """Get the status for a server.  Anyone can request this,

    :param name: Name of VApp which we want to stop.
    :returns: The state, by name.
    """
    vm_id, actor_id = _resolve_vm(request)
    return server.check_state(vm_id)

def _set_server_state(request, target_state):
    """Basic function for putting a server into some state, for basic state-change calls."""
    vm_id, actor_id = _resolve_vm(request)
    return {"vm_id": vm_id,
            "touch_id": server.touch_to_state(actor_id, vm_id, target_state)}

#Pyramid is not designed to allow you to add view configurations programatically.
#But in Python all things are possible.  Here is a way to set up view configurations in a loop.
#This will declare the functions "set_server_to_Boosting", etc...
#And bind them to the routes "server_Boosting" and "server_by_id_Boosting"

### Here are the states that can only be set by agents...
for state in ['Stopped', 'Started', 'Prepared', 'Pre_Deboosted',
              'Boosting', 'Deboosting', 'Starting_Boosted' ]:
     funcname = 'set_server_to_' + state
     globals()[funcname] = lambda request, state=state: _set_server_state(request, state)
     globals()[funcname] = view_config( request_method="POST",
                                        routes=['server_' + state, 'server_by_id_' + state],
                                        renderer='json',
                                        permission="act"
                                      )( globals()[funcname] )
     globals()[funcname].__name__ = funcname
     globals()[funcname].__qualname__ = funcname

### States that any user can put their server into...
for state in ['Starting', 'Stopping', 'Restarting', 'Error']:
     funcname = 'set_server_to_' + state
     globals()[funcname] = lambda request, state=state: _set_server_state(request, state)
     globals()[funcname] = view_config( request_method="POST",
                                        routes=['server_' + state, 'server_by_id_' + state],
                                        renderer='json',
                                        permission="use"
                                      )( globals()[funcname] )
     globals()[funcname].__name__ = funcname
     globals()[funcname].__qualname__ = funcname

### Any user can Boost, but it will cost.
@view_config(request_method="POST", routes=['server_Preparing', 'server_by_id_Preparing'],
             renderer='json', permission="use")
def boost_server(request):
    """Boost a server: ie:
        Debit the users account
        Schedule a De-Boost
        Set the CPUs and RAM
        Put the server in a "preparing" status

    :param {vm or name}: ID of VApp which we want to boost.
    :ram: ram wanted
    :cores: cores wanted
    :hours: hours of boost wanted
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    vm_id, actor_id = _resolve_vm(request)

    hours = int(request.POST['hours'])
    cores = int(request.POST['cores'])
    ram   = int(request.POST['ram'])

    # FIXME: Really the user should boost to a named level, rather than directly
    # specifying RAM and cores.  For now I'm just going to work out the cost based
    # on the cores requested, and assume the RAM level matches it.
    cost = server.check_and_remove_credits(actor_id, ram, cores, hours)

    if not cost:
        #Either we can't afford it or we can't determine the cost.
        return HTTPBadRequest();

    #Schedule a de-boost
    server.touch_to_add_deboost(vm_id, hours)

    # Set spec
    server.touch_to_add_specification(vm_id, cores, ram)

    # Tell the agents to get to work.
    touch_id = server.touch_to_state(actor_id, vm_id, "Preparing")

    return dict(touch_id=touch_id, vm_id=vm_id, cost=cost)

# Likewise any user can deboost.
@view_config(request_method="POST", routes=['server_Pre_Deboosting', 'server_by_id_Pre_Deboosting'],
             renderer='json', permission="use")
def deboost_server(request):
    """Deboost a server: ie:
        Credit the users account
        Cancel any scheduled De-Boost
        Set the CPUs and RAM to the previous state
        Put the server in a "Pre_Deboosting" status

    Note that a user can Deboost at ANY time, but they only get credit if credit is due.
    Deboosting a non-boosted server just amounts to a restart.

    :param {vm or name}: ID of VApp which we want to deboost.
    :returns: dict(touch_id, vm_id, credit) where credit is the refunded amount
    """
    vm_id, actor_id = _resolve_vm(request)

    credit = server.get_time_until_deboost(vm_id)[3]
    server.touch_to_add_credit(actor_id, credit)

    #Scheduled timeouts don't need cancelling as they are ignored on unboosted servers,
    #and if the user re-boosts then the new timeout will mask the old one.

    #This call will return the baseline if there is no previous spec.
    prev_cores, prev_ram = server.get_previous_specification(vm_id)

    #If we're not careful, with this "go back to previous config" semantics, if a user de-boosts
    #a server twice they will actually end up setting their baseline config to the boosted specs.
    #Therefore do a check.
    current_cores, current_ram = server.get_latest_specification(vm_id)

    if not (prev_ram > current_ram):
        server.touch_to_add_specification(vm_id, prev_cores, prev_ram)

    # Tell the agents to get to work.
    touch_id = server.touch_to_state(actor_id, vm_id, "Pre_Deboosting")

    return dict(touch_id=touch_id, vm_id=vm_id, credit=credit)

@view_config(request_method="POST", routes=['server_extend_boost', 'server_by_id_extend_boost'],
             renderer='json', permission="use")
def extend_boost_on_server(request):
    """Extends the Boost period on a server by adding a new deboost timeout, if
       the user can afford it, and debiting the cost.
    """
    vm_id, actor_id = _resolve_vm(request)
    hours = int(request.POST['hours'])

    #See what level of boost we have just now.
    cores, ram = server.get_latest_specification(vm_id)

    cost = server.check_and_remove_credits(actor_id, ram, cores, hours)

    if not cost:
        #Either we can't afford it or we can't determine the cost.
        return HTTPBadRequest();

    #Work out when the new de-boost should be.  First get the remaining boost time as
    #hours.  It's unlikely to be a whole number.  If the boost has expired somehow then
    #don't be mean - count from now.
    remaining_time = (server.get_time_until_deboost(vm_id)[1] or 0) / 3600.0
    if remaining_time < 0 : remaining_time = 0

    #Schedule a later de-boost
    server.touch_to_add_deboost(vm_id, hours + remaining_time)

    return dict(vm_id=vm_id, cost=cost)

# Find out what needs de-boosting (agents only)
@view_config(request_method="GET", route_name='deboosts', renderer='json', permission="act")
def deboost_jobs(request):
    """ Calls get_deboost_jobs, which is what the deboost_daemon needs in order to work.
        Defaults to getting all deboosts that expired within the last 60 minutes.
    """
    past = int(request.params.get('past', 60))
    future = int(request.params.get('future', 0))

    return server.get_deboost_jobs(past, future)


@view_config(request_method="GET", route_name='server_touches', renderer='json', permission="use")
def retrieve_server_touches(request):
    """ Retrieve activity log from recent touches. """
    # FIXME - Clearly this hasn't been implemented.
    name = request.matchdict['name']
    return name

@view_config(request_method="POST", renderer='json', permission="act",
             routes=['server_specification', 'server_by_id_specification'])
def set_server_specification(request):
    """ Set number of cores and amount of RAM for a VM directly.

        Regular users can only do this indirectly via boost/deboost, which
        will check that the levels match one of the approved values.
    """
    vm_id, actor_id = _resolve_vm(request)

    cores = int(request.POST.get('cores'))
    ram = int(request.POST.get('ram'))
    if (cores <= 0) or (ram <= 0):
        return HTTPBadRequest()
    else:
        server.touch_to_add_specification(vm_id, cores, ram)
        return dict(cores=cores, ram=ram, artifact_id=vm_id)

@view_config(request_method="GET", renderer='json', permission="use",
             routes=['server_specification', 'server_by_id_specification'])
def get_server_specification(request):
    """ Get the specification of a machine. Returns RAM in GB and number of
    cores in a JSON object."""
    vm_id, actor_id = _resolve_vm(request)

    cores, ram = server.get_latest_specification(vm_id)
    return dict(cores=cores, ram=ram, artifact_id=vm_id)

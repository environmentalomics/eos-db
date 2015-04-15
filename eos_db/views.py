"""API functions for controlling the Cloudhands DB

This module contains all the API functions available on the Cloudhands RESTful
API. Modifications requests to the database are mediated through functions in
the "server" module.
"""

import json, uuid, bcrypt
import hashlib, base64, random
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotImplemented, HTTPUnauthorized, HTTPForbidden, HTTPNotFound
from pyramid.security import Allow, Everyone

from eos_db import server

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
    """ Return a list of all valid API calls. """
    call_list = {"Valid API Call List":{
                              "Setup States": "/setup_states",
                              "Sessions": "/sessions",
                              "session": "/session",  # Get session details or
                              "users": "/users",  # Return user list
                              "user": "/user",  # Get logged-in user details or
                              "user_touches": "/user/touches",
                              "user_password": "/user/password",
                              "user_credit": "/user/credit",
                              "servers": "/servers",  # Return server list
                              "server": "/servers/{name}",  # Get server details or
                              "server_by_id": "/servers/by_id/{name}",
                              "states": "/states/{name}",  # Get list of servers in given state.
                              "server_start": "/servers/{name}/start",
                              "server_stop": "/servers/{name}/stop",
                              "server_restart": "/servers/{name}/restart",
                              "server_pre_deboost": "/servers/{name}/pre_deboosting",
                              "server_pre_deboosted": "/servers/{name}/Pre_deboosted",
                              "server_deboost": "/servers/{name}/deboosting",
                              "server_deboosted": "/servers/{name}/Deboosted",
                              "server_started": "/servers/{name}/Started",
                              "server_stopped": "/servers/{name}/Stopped",
                              "server_prepare": "/servers/{name}/prepare",
                              "server_prepared": "/servers/{name}/prepared",
                              "server_boost": "/servers/{name}/boost",
                              "server_boosted": "/servers/{name}/boosted",
                              "server_suspend": "/servers/{name}/suspend",
                              "server_owner": "/servers/{name}/owner",
                              "server_touches": "/servers/{name}/touches",
                              "server_job_status": "/servers/{name}/job/{job}/status",
                              "server_specification": "/servers/{name}/specification"
                              }
                 }
    return call_list

# OPTIONS call result

@view_config(request_method="OPTIONS", route_name='servers', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_start', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_stop', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_restart', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_pre_deboost', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_prepare', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_specification', renderer='json')
def options(request):
    """ Return the OPTIONS header. """
    # FIXME: This is important for enabling CORS, although under certain
    # circumstances the browser doesn' appear to need it. Might be worth
    # examining why.
    # FIXME2 - I don't think this is even used.  See the options callback instead.
    return None

@view_config(request_method="POST", route_name='setup', renderer='json', permission="use")
def setup(request):
    """ Deploy tables into a database. """
    #server.choose_engine("SQLite")
    server.deploy_tables()
    return None

# FIXME - permission=admisister, surely??  And for the one above.
@view_config(request_method="POST", route_name='setup_states', renderer='json', permission="use")
def setup_states(request):
    """ Deploy list of valid artifact states into database. The states are in server.py
        and may be supplemented in settings.py
    """
    server.setup_states()
    return None

@view_config(request_method="GET", route_name='users', renderer='json', permission="use")
def retrieve_users(request):
    # FIXME: Do these need to be here? Or are they worth having as a placeholder?
    return HTTPNotImplemented()

@view_config(request_method="PUT", route_name='user', renderer='json', permission="use")
def create_user(request):
    """ Create a user in the database. """
    newname = server.create_user(request.POST['type'], request.POST['handle'], request.POST['name'], request.matchdict['name'])
    return newname

@view_config(request_method="GET", route_name='user', renderer='json', permission="use")
def retrieve_user(request):
    """Return account details for a user.

    :param actor_id: The user we are interested in.
    :returns JSON object containing user table data and credit balance.
    """
    # username = request.matchdict['name']
    username = request.authenticated_userid
    actor_id = server.get_user_id_from_name(username)
    if server.check_actor_id(username) == False:
        return HTTPForbidden()
    details = server.check_user_details(username)
    details['credits'] = server.check_credit(actor_id)
    return json.dumps(details)

@view_config(request_method="PATCH", route_name='user', renderer='json', permission="use")
def update_user(request):
    # FIXME: Not implemented.
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='user', renderer='json', permission="use")
def delete_user(request):
    # FIXME: Not implemented. Some thought needs to go into this. I think a
    # deletion flag would be appropriate, but this will involve changing quite
    # a number of queries.
    response = HTTPNotImplemented()
    return response

@view_config(request_method="PUT", route_name='user_password', renderer='json', permission="administer")
def create_user_password(request):
    """ Creates a password for the user given. """
    username = request.matchdict['name']
    actor_id = server.get_user_id_from_name(username)
    newname = server.touch_to_add_password(actor_id, request.POST['password'])
    return newname

@view_config(request_method="GET", route_name='user_password', renderer='json', permission="use")
def retrieve_user_password(request):
    """ Standard login method. Basicauth is used for authorisation, so this
    just checks that the user whose details we are requesting matches the
    details passed from BasicAuth. """

    username = request.matchdict['name']
    actor_id = server.get_user_id_from_name(username)
    bapauth = request.authenticated_userid
    print (bapauth)
    return True if (bapauth == username) else None

@view_config(request_method="GET", route_name='user_touches', renderer='json', permission="use")
def retrieve_user_touches(request):
    # FIXME - Not implemented.
    name = request.matchdict['name']
    return name

@view_config(request_method="POST", route_name='user_credit', renderer='json', permission="administrate")
def create_user_credit(request):
    """Adds credit to a user account, negative or positive.

    Checks if actor_id is valid, otherwise throws HTTP 403.
    Checks if credit is an integer, otherwise throws HTTP 400.

    :returns: JSON containing actor id, credit change and new balance.
    """
    actor_id, credit = request.matchdict['name'], request.POST['credit']
    if credit.lstrip('-').isdigit() == False:
        return HTTPBadRequest()
    if server.check_actor_id(actor_id) == False:
        return HTTPUnauthorized()
    user_id = server.get_user_id_from_name(actor_id)
    server.touch_to_add_credit(user_id, credit)
    credits = server.check_credit(actor_id)
    output = json.dumps({'actor_id': int(user_id),
                         'credit_change': int(credit),
                         'credit_balance': int(credits)}, sort_keys=True)
    return output

@view_config(request_method="GET", route_name='user_credit', renderer='json', permission="use")
def retrieve_user_credit(request):
    """Return credits outstanding for a user.

    :param actor_id: Actor/user id for which we are checking credit.
    :returns: JSON containing actor_id and current balance.
    """
    username = request.matchdict['name']
    actor_id = server.get_user_id_from_name(username)
    if server.check_actor_id(username) == False:
        return HTTPNotFound()
    credits = server.check_credit(username)
    output = json.dumps({'actor_id': actor_id,
                         'credit_balance': int(credits)}, sort_keys=True)
    return output

@view_config(request_method="GET", route_name='servers', renderer='json', permission="use")
def retrieve_servers(request):
    """
    Lists all artifacts related to a given user.
    """
    print ("Servers for user: " + request.authenticated_userid)
    server_list = server.list_artifacts_for_user(request.authenticated_userid)
    print (server_list)
    return server_list

@view_config(request_method="GET", route_name='state', renderer='json', permission="use")
def retrieve_servers_in_state(request):
    """
    Lists all servers in a given state.
    """
    server_id = server.list_server_in_state(request.GET['state'])
    server_uuid = server.get_server_uuid_by_id(server_id)
    return {"artifact_id": server_id, "artifact_uuid":server_uuid}

@view_config(request_method="PUT", route_name='server', renderer='json', permission="use")
def create_server(request):
    """
    Creates a new artifact record in the database.
    """
    newname = server.create_appliance(request.matchdict['name'], request.POST['uuid'])
    return newname

@view_config(request_method="GET", route_name='server', renderer='json', permission="use")
def retrieve_server(request):
    """
    Gets artifact details from the server.
    """
    name = request.matchdict['name']
    server_id = server.get_server_id_from_name(name)
    server_details = server.return_artifact_details(server_id)
    return server_details

@view_config(request_method="GET", route_name='server_by_id', renderer='json', permission="use")
def retrieve_server_by_id(request):
    """
    Gets artifact details, but uses the internal system ID.
    """
    id = request.matchdict['name']
    server_details = server.return_artifact_details(id)
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
    # Not implemented. Check if necessary.
    return HTTPNotImplemented()

@view_config(request_method="POST", route_name='server_start', renderer='json', permission="use")
def start_server(request):
    """Put a server into the "pre-start" status.

    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    # FIXME: Should be able to roll these state change views up into a single call.
    if server.check_token(request.headers['eos_token'], request.matchdict['name']):
        newname = server.touch_to_state(request.matchdict['name'], "Starting")
        return newname
    else:
        return HTTPUnauthorized

@view_config(request_method="POST", route_name='server_restart', renderer='json', permission="use")
def restart_server(request):
    """Put a server into the "restart" status.

    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    # FIXME: Should be able to roll these state change views up into a single call.
    touch_id = server.touch_to_state(request.matchdict['name'], "Restarting")
    return touch_id

@view_config(request_method="POST", route_name='server_stop', renderer='json', permission="use")
def stop_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    # FIXME: Should be able to roll these state change views up into a single call.
    touch_id = server.touch_to_state(request.matchdict['name'], "Stopping")
    return touch_id

@view_config(request_method="POST", route_name='server_prepare', renderer='json', permission="use")
def prepare_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    # FIXME: Should be able to roll these state change views up into a single call.
    touch_id = server.touch_to_state(request.matchdict['name'], "Preparing")
    return touch_id

@view_config(request_method="GET", route_name='server_state', renderer='json', permission="use")
def server_state(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    id = server.get_server_id_from_name(request.matchdict['name'])
    newname = server.check_state(id)
    return newname

@view_config(request_method="POST", route_name='server_pre_deboost', renderer='json', permission="use")
def pre_deboost_server(request):
    """Put a server into the "pre-deboost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    # FIXME: Should be able to roll these state change views up into a single call.
    touch_id = server.touch_to_state(request.matchdict['name'], "Pre_Deboosting")
    return touch_id

@view_config(request_method="POST", route_name='server_boost', renderer='json', permission="use")
def boost_server(request):
    """Put a server into the "pre-boost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Boosting")  # Boost Server
    # FIXME: I'd commented this part of the code out to work on other things.
    # Should just be decommentable.

    # Now check if boost was successful, set deboost and remove credits accordingly.
    # if touch_id:
    #    credit_change = server.check_and_remove_credits(request.POST['vm_id'],
    #                                                    request.POST['ram'],
    #                                                    request.POST['cores'],
    #                                                    request.POST['hours'])
    #    server.touch_to_add_deboost(request.POST['vm_id'], request.POST['hours'])
    # return credit_change


@view_config(request_method="POST", route_name='server_stopped', renderer='json', permission="use")
def stopped_server(request):
    """Put a server into the "Stopped" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Stopped")
    return touch_id

@view_config(request_method="POST", route_name='server_started', renderer='json', permission="use")
def started_server(request):
    """Put a server into the "Started" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Started")
    return touch_id

@view_config(request_method="POST", route_name='server_error', renderer='json', permission="use")
def error_server(request):
    """Put a server into the "Started" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Error")
    return touch_id

@view_config(request_method="POST", route_name='server_prepared', renderer='json', permission="use")
def prepared_server(request):
    """Put a server into the "Prepared" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Prepared")
    return touch_id

@view_config(request_method="POST", route_name='server_pre_deboosted', renderer='json', permission="use")
def predeboosted_server(request):
    """Put a server into the "Pre_Deboosted" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.matchdict['name'], "Pre_Deboosted")
    return touch_id

@view_config(request_method="GET", route_name='server_job_status', renderer='json', permission="use")
def retrieve_job_progress(request):
    """Put a server into the "pre-stop" status.

    :param job_id: Internal job ID related to current task.
    :returns: JSON containing VApp ID and status.
    """
    newname = server.check_progress(request.matchdict['job'])
    return newname

@view_config(request_method="GET", route_name='server_touches', renderer='json', permission="use")
def retrieve_server_touches(request):
    """ Retrieve activity log from recent touches. """
    # FIXME - Clearly this hasn't been implemented.
    name = request.matchdict['name']
    return name

@view_config(request_method="POST", route_name='server_specification', renderer='json', permission="use")
def set_server_specification(request):
    """ Set number of cores and amount of RAM for a VM. These numbers should
    only match the given specification types listed below. """

    # FIXME: This also needs to look up the other servers currently boosted
    # and return a bad request if there is not enough capacity.

    name = request.matchdict['name']
    vm_id = server.get_server_id_from_name(name)

    # Filter for bad requests
    # FIXME - check against valid machine states in settings.py

    if (request.POST['cores'] not in ['1', '2', '4', '16']) or (request.POST['ram'] not in ['1', '4', '8', '16', '500']):
        # FIXME - This really shouldn't be hardcoded.
        return HTTPBadRequest()
    else:
        server.touch_to_add_specification(vm_id, request.POST['cores'], request.POST['ram'])
        return name

@view_config(request_method="GET", route_name='server_specification', renderer='json', permission="use")
def get_server_specification(request):
    """ Get the specification of a machine. Returns RAM in GB and number of
    cores in a JSON object."""
    name = request.matchdict['name']
    vm_id = server.get_server_id_from_name(name)
    cores, ram = server.get_latest_specification(vm_id)
    return {"cores":cores, "ram":ram}

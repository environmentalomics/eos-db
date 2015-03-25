"""API functions for controlling the Cloudhands DB

This module contains all the API functions available on the Cloudhands RESTful
API. Modifications requests to the database are mediated through functions in
the "server" module.
"""

##############################################################################

import json

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotImplemented, HTTPUnauthorized, HTTPForbidden
import hashlib, base64, random
from eos_db import server

##############################################################################

# Home View

@view_config(request_method="GET", route_name='home', renderer='json')
def home_view(request):
    call_list = {"Valid API Call List":{
                              "Setup States": "/setup_states",
                              "Sessions": "/sessions",
                              "session": "/session", # Get session details or
                              "users": "/users", # Return user list
                              "user": "/users/{name}",   # Get user details or
                              "user_touches": "/users/{name}/touches",
                              "user_password": "/users/{name}/password",
                              "user_credit": "/users/{name}/credit",
                              "servers": "/servers", # Return server list
                              "server": "/servers/{name}",    # Get server details or
                              "server_by_id": "/servers/by_id/{name}",
                              "states": "/states/{name}", # Get list of servers in given state.
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

@view_config(request_method="OPTIONS", route_name='server_start', renderer='json', permission="token")
@view_config(request_method="OPTIONS", route_name='server_stop', renderer='json', permission="token")
def options(request):
    return "None"

# Views for setting up test databases

@view_config(request_method="POST", route_name='setup', renderer='json', permission="use")
def setup(request):
    server.choose_engine("SQLite")
    server.deploy_tables()
    return None

@view_config(request_method="POST", route_name='setup_states', renderer='json', permission="use")
def setup_states(request):
    server.setup_states(['Starting',
                         'Started',
                         'Stopping',
                         'Stopped',
                         'Pre_Deboosting',
                         'Pre_Deboosted',
                         'Preparing',
                         'Prepared',
                         'Boosting',
                         'Boosted',
                         'Restarting'])
    return None

# User-related API calls - All users

@view_config(request_method="GET", route_name='users', renderer='json', permission="use")
def retrieve_users(request):
    return HTTPNotImplemented()

# User-related API calls - Individual users

@view_config(request_method="PUT", route_name='user', renderer='json', permission="use")
def create_user(request):
    newname = server.create_user(request.POST['type'],request.POST['handle'],request.POST['name'],request.POST['username'])
    return newname

@view_config(request_method="GET", route_name='user', renderer='json', permission="use")
def retrieve_user(request):
    """Return account details for a user.
    :param actor_id: The user we are interested in.
    :returns JSON object containing user table data and credit balance.
    """
    actor_id = request.GET['actor_id']
    if server.check_actor_id(actor_id) == False:
        return HTTPForbidden()
    details = server.check_user_details(actor_id)
    details['credits'] = server.check_credit(actor_id)
    return json.dumps(details)

@view_config(request_method="PATCH", route_name='user', renderer='json', permission="use")
def update_user(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='user', renderer='json', permission="use")
def delete_user(request):
    response = HTTPNotImplemented()
    return response

# User password actions

@view_config(request_method="PUT", route_name='user_password', renderer='json', permission="use")
def create_user_password(request):
    # Add salt and hash
    newname = server.touch_to_add_password(request.POST['actor_id'],request.POST['password'])
    return newname

@view_config(request_method="GET", route_name='user_password', renderer='json', permission="use")
def retrieve_user_password(request):
    # Add salt and hash
    verify = server.check_password(request.GET['actor_id'],request.GET['password'])
    if verify == True:
        key = base64.b64encode(hashlib.sha256( str(random.getrandbits(256)) ).digest(), random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')
        server.touch_to_add_session_key(request.GET['actor_id'], key)
        return key
    else:
        response = HTTPUnauthorized()
        return response


# Retrieve activity log from recent touches

@view_config(request_method="GET", route_name='user_touches', renderer='json', permission="use")
def retrieve_user_touches(request):
    name = request.matchdict['name']
    return name

# User credit addition, querying etc.

@view_config(request_method="POST", route_name='user_credit', renderer='json', permission="use")
def create_user_credit(request):
    """Adds credit to a user account, negative or positive.

    Checks if actor_id is valid, otherwise throws HTTP 403.
    Checks if credit is an integer, otherwise throws HTTP 400.

    :returns: JSON containing actor id, credit change and new balance.
    """
    actor_id, credit = request.POST['actor_id'], request.POST['credit']
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
    actor_id = request.GET['actor_id']
    if server.check_actor_id(actor_id) == False:
        return HTTPNotFound()
    credits = server.check_credit(actor_id)
    output = json.dumps({'actor_id': actor_id,
                         'credit_balance': int(credits)}, sort_keys=True)
    return output

##############################################################################

# Server-related API calls - All Servers

@view_config(request_method="GET", route_name='servers', renderer='json', permission="use")
def retrieve_servers(request):
    server_list = server.list_artifacts_for_user(request.GET['actor_id'])
    return server_list

@view_config(request_method="GET", route_name='states', renderer='json', permission="use")
def retrieve_servers_in_state(request):
    server_id = server.list_server_in_state(request.GET['state'])
    server_uuid = server.get_server_uuid_by_id(server_id)
    return {"artifact_id": server_id, "artifact_uuid":server_uuid}

# Server-related API calls - Individual Servers

@view_config(request_method="PUT", route_name='server', renderer='json', permission="use")
def create_server(request):
    newname = server.create_appliance(request.POST['hostname'], request.POST['uuid'])
    return newname

@view_config(request_method="GET", route_name='server', renderer='json', permission="use")
def retrieve_server(request):
    name = request.matchdict['name']
    server_id = server.get_server_id_from_name(name)
    server_details = server.return_artifact_details(server_id)
    return server_details

@view_config(request_method="GET", route_name='server_by_id', renderer='json', permission="use")
def retrieve_server_by_id(request):
    id = request.matchdict['name']
    server_details = server.return_artifact_details(id)
    return server_details

@view_config(request_method="PATCH", route_name='server', renderer='json', permission="use")
def update_server(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='server', renderer='json', permission="use")
def delete_server(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="PUT", route_name='server_owner', renderer='json', permission="use")
def create_server_owner(request):
    newname = server.touch_to_add_ownership(request.POST['artifact_id'], request.POST['actor_id'])
    return newname

@view_config(request_method="GET", route_name='server_owner', renderer='json', permission="use")
def get_server_owner(request):
    return HTTPNotImplemented

# State changes

@view_config(request_method="POST", route_name='server_start', renderer='json', permission="token")
def start_server(request):
    """Put a server into the "pre-start" status.

    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    if server.check_token(request.POST['eos_token'], request.POST['vm_id']):
        touch_id = server.touch_to_state(request.POST['vm_id'], "Starting")
        return touch_id
    else:
        return HTTPUnauthorized

@view_config(request_method="POST", route_name='server_restart', renderer='json', permission="token")
def restart_server(request):
    """Put a server into the "restart" status.

    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Restarting")
    return touch_id

@view_config(request_method="POST", route_name='server_stop', renderer='json', permission="use")
def stop_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Stopping")
    return touch_id

@view_config(request_method="POST", route_name='server_prepare', renderer='json', permission="use")
def prepare_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Preparing")
    return touch_id

@view_config(request_method="GET", route_name='server_state', renderer='json', permission="use")
def server_state(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    id = server.get_server_id_from_name(request.GET['artifact_id'])
    newname = server.check_state(id)
    return newname

@view_config(request_method="POST", route_name='server_pre_deboost', renderer='json', permission="use")
def pre_deboost_server(request):
    """Put a server into the "pre-deboost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'],  "Pre_Deboosting")
    return touch_id

@view_config(request_method="POST", route_name='server_boost', renderer='json', permission="use")
def boost_server(request):
    """Put a server into the "pre-boost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Boosting") # Boost Server

    # Now check if boost was successful, set deboost and remove credits accordingly.
    #if touch_id:
    #    credit_change = server.check_and_remove_credits(request.POST['vm_id'],
    #                                                    request.POST['ram'],
    #                                                    request.POST['cores'],
    #                                                    request.POST['hours'])
    #    server.touch_to_add_deboost(request.POST['vm_id'], request.POST['hours'])
    #return credit_change


@view_config(request_method="POST", route_name='server_stopped', renderer='json', permission="use")
def stopped_server(request):
    """Put a server into the "Stopped" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Stopped")
    return touch_id

@view_config(request_method="POST", route_name='server_started', renderer='json', permission="use")
def started_server(request):
    """Put a server into the "Started" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Started")
    return touch_id

@view_config(request_method="POST", route_name='server_prepared', renderer='json', permission="use")
def prepared_server(request):
    """Put a server into the "Prepared" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Prepared")
    return touch_id

@view_config(request_method="POST", route_name='server_pre_deboosted', renderer='json', permission="use")
def predeboosted_server(request):
    """Put a server into the "Pre_Deboosted" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_state(request.POST['vm_id'], "Pre_Deboosted")
    return touch_id

@view_config(request_method="GET", route_name='server_job_status', renderer='json', permission="use")
def retrieve_job_progress(request):
    """Put a server into the "pre-stop" status.

    :param job_id: Internal job ID related to current task.
    :returns: JSON containing VApp ID and status.
    """
    newname = server.check_progress(request.GET['job_id'])
    return newname

# Retrieve activity log from recent touches

@view_config(request_method="GET", route_name='server_touches', renderer='json', permission="use")
def retrieve_server_touches(request):
    name = request.matchdict['name']
    return name

# Server specification calls

@view_config(request_method="POST", route_name='server_specification', renderer='json', permission="use")
def set_server_specification(request):
    name = request.matchdict['name']
    vm_id = server.get_server_id_from_name(name)
    
    # Filter for bad requests
    
    if (request.POST['cores'] not in ['1','2','4','16']) or (request.POST['ram'] not in ['1','4','8','16','500']):
        return HTTPBadRequest()
    else:
        server.touch_to_add_specification(vm_id, request.POST['cores'], request.POST['ram'])
        return name

@view_config(request_method="GET", route_name='server_specification', renderer='json', permission="use")
def get_server_specification(request):
    name = request.matchdict['name']
    vm_id = server.get_server_id_from_name(name)
    cores, ram = server.get_latest_specification(vm_id)
    return {"cores":cores,"ram":ram}



##############################################################################

# Session-related API calls TODO


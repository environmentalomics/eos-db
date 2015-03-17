"""API functions for controlling the Cloudhands DB

This module contains all the API functions available on the Cloudhands RESTful
API. Modifications requests to the database are mediated through functions in
the "server" module.
"""

##############################################################################

import json

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotImplemented, HTTPUnauthorized, HTTPForbidden

from eos_db import server, auth

##############################################################################

# Home View

@view_config(request_method="GET", route_name='home', renderer='json')
def home_view(request):
    return None

# OPTIONS call result

@view_config(request_method="OPTIONS", route_name='server_start', renderer='json')
@view_config(request_method="OPTIONS", route_name='server_stop', renderer='json')
def options(request):
    return "None"

# Views for setting up test databases

@view_config(request_method="POST", route_name='setup_states', renderer='json')
def setup_states(request):
    return None

@view_config(request_method="POST", route_name='setup', renderer='json')
def setup(request):
    return None

# User-related API calls - All users

@view_config(request_method="GET", route_name='users', renderer='json')
def retrieve_users(request):
    return name

# User-related API calls - Individual users

@view_config(request_method="PUT", route_name='user', renderer='json')
def create_user(request):
    newname = server.create_user(request.POST['type'],request.POST['handle'],request.POST['name'],request.POST['username'])
    return newname

@view_config(request_method="GET", route_name='user', renderer='json')
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

@view_config(request_method="PATCH", route_name='user', renderer='json')
def update_user(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='user', renderer='json')
def delete_user(request):
    response = HTTPNotImplemented()
    return response

# User password actions

@view_config(request_method="PUT", route_name='user_password', renderer='json')
def create_user_password(request):
    # Add salt and hash
    newname = server.touch_to_add_password(request.POST['actor_id'],request.POST['password'])
    return newname

@view_config(request_method="GET", route_name='user_password', renderer='json')
def retrieve_user_password(request):
    # Add salt and hash
    verify = server.check_password(request.GET['actor_id'],request.GET['password'])
    if verify == True:
        return 'a8a89098a0e9'
    else:
        response = HTTPUnauthorized()
        return response


# Retrieve activity log from recent touches

@view_config(request_method="GET", route_name='user_touches', renderer='json')
def retrieve_user_touches(request):
    name = request.matchdict['name']
    return name

# User credit addition, querying etc.

@view_config(request_method="POST", route_name='user_credit', renderer='json')
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
        return HTTPForbidden()
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
        return HTTPForbidden()
    credits = server.check_credit(actor_id)
    output = json.dumps({'actor_id': int(actor_id),
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
    server_list = server.list_server_in_state(request.GET['state'])
    return server_list

# Server-related API calls - Individual Servers

@view_config(request_method="PUT", route_name='server', renderer='json', permission="use")
def create_server(request):
    newname = server.create_appliance(request.POST['hostname'])
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

# State changes

@view_config(request_method="POST", route_name='server_start', renderer='json', permission="use")
def start_server(request):
    """Put a server into the "pre-start" status.

    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_prestart(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_restart', renderer='json', permission="use")
def restart_server(request):
    """Put a server into the "restart" status.
    
    :param vm_id: ID of VApp which we want to start.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """   
    newname = server.touch_to_restart(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_stop', renderer='json', permission="use")
def stop_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_prestop(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_prepare', renderer='json', permission="use")
def prepare_server(request):
    """Put a server into the "pre-stop" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_prepare(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_pre_deboost', renderer='json', permission="use")
def pre_deboost_server(request):
    """Put a server into the "pre-deboost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_pre_deboost(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_boost', renderer='json', permission="use")
def boost_server(request):
    """Put a server into the "pre-boost" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    touch_id = server.touch_to_boost(request.POST['vm_id']) # Boost Server

    # Now check if boost was successful, set deboost and remove credits accordingly.
    if touch_id:
        credit_change = server.check_and_remove_credits(request.POST['vm_id'],
                                                        request.POST['ram'],
                                                        request.POST['cores'],
                                                        request.POST['hours'])
        server.touch_to_add_deboost(request.POST['vm_id'], request.POST['hours'])
    return credit_change


@view_config(request_method="POST", route_name='server_stopped', renderer='json', permission="use")
def stopped_server(request):
    """Put a server into the "Stopping" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_stop(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_started', renderer='json', permission="use")
def started_server(request):
    """Put a server into the "Starting" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_start(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_prepared', renderer='json', permission="use")
def prepared_server(request):
    """Put a server into the "Starting" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_prepared(request.POST['vm_id'])
    return newname

@view_config(request_method="POST", route_name='server_pre_deboosted', renderer='json', permission="use")
def predeboosted_server(request):
    """Put a server into the "Starting" status.

    :param vm_id: ID of VApp which we want to stop.
    :returns: JSON containing VApp ID and job ID for progress calls.
    """
    newname = server.touch_to_predeboosted(request.POST['vm_id'])
    return newname

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


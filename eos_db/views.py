"""API functions for controlling the Cloudhands DB

This module contains all the API functions available on the Cloudhands RESTful
API. Modifications requests to the database are mediated through functions in
the "server" module.
"""

##############################################################################

import json

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotImplemented, HTTPUnauthorized, HTTPForbidden

from eos_db import server

##############################################################################

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
    name = request.matchdict['name']
    return name

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

@view_config(request_method="PUT", route_name='user_credit', renderer='json')
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
    server.touch_to_add_credit(actor_id, credit)
    credits = server.check_credit(actor_id)
    output = json.dumps({'actor_id': int(actor_id),
                         'credit_change': int(credit),
                         'credit_balance': int(credits)}, sort_keys=True)
    return output

@view_config(request_method="GET", route_name='user_credit', renderer='json')
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

@view_config(request_method="GET", route_name='servers', renderer='json')
def retrieve_servers(request):
    server_list = server.list_artifacts_for_user(request.GET['actor_id'])
    return server_list

# Server-related API calls - Individual Servers

@view_config(request_method="PUT", route_name='server', renderer='json')
def create_server(request):
    newname = server.create_appliance(request.POST['hostname'])
    return newname

@view_config(request_method="GET", route_name='server', renderer='json')
def retrieve_server(request):
    name = request.matchdict['name']
    return name

@view_config(request_method="PATCH", route_name='server', renderer='json')
def update_server(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="DELETE", route_name='server', renderer='json')
def delete_server(request):
    response = HTTPNotImplemented()
    return response

@view_config(request_method="PUT", route_name='server_owner', renderer='json')
def create_server_owner(request):
    newname = server.touch_to_add_ownership(request.POST['artifact_id'], request.POST['actor_id'])
    return newname

# Retrieve activity log from recent touches

@view_config(request_method="GET", route_name='server_touches', renderer='json')
def retrieve_server_touches(request):
    name = request.matchdict['name']
    return name


##############################################################################

# Session-related API calls TODO


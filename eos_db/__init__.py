from pyramid.config import Configurator
from pyramid.events import NewRequest

import logging
import os
import eos_db.server

from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.httpexceptions import HTTPUnauthorized

ALLOWED_ORIGIN = ('http://localhost:6542', )

def add_cors_headers_response_callback(event):

    def cors_headers(request, response):
        log = logging.getLogger(__name__)
        if 'Origin' in request.headers:
            origin = request.headers['Origin']
            if origin in ALLOWED_ORIGIN:
                log.debug('Access Allowed')
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    event.request.add_response_callback(cors_headers)

def passwordcheck():
    """Generates a callback supplied to BasicAuthAuthenticationPolicy to check
       the password.
    """

    #Bcrypy is slow, which is good to deter dictionary attacks, but bad when
    #the same user is calling multiple API calls, and especially bad for the tests.
    #This one-item cache should be crude but effective:
    lastpass = [""]

    def _passwordcheck(login, password, request):
        #print("Checking %s:%s for %s" % (login, password, request))
        #print("Lastpass is " + lastpass[0])

        if ( str(lastpass[0]) == login + ":" + password or
             eos_db.server.check_password(login, password) ):

                user_group = eos_db.server.get_user_group(login)[0]

                if user_group in ("administrators", "users", "agents"):
                    #Remember that this worked
                    lastpass[0] = login + ":" + password
                    return ['group:' + user_group]
                else:
                    lastpass[0] = ""
                    return None
        else:
            lastpass[0] = ""
            return None

    return _passwordcheck

def basic_challenge(basicauthpolicy):
    """Fire a 401 when authentication needed
       The reason for capturing the BasicAuthAuthenticationPolicy in a closure
       is because it knows the right realm and thus will generate the right headers.
    """

    def _basic_challenge(request):
        response = HTTPUnauthorized()
        response.headers.update(basicauthpolicy.forget(request))
        return response

    return _basic_challenge

def main(global_config, **settings):

    bap = BasicAuthAuthenticationPolicy(check=passwordcheck(), realm="eos_db")
    config = Configurator(settings=settings,
                          authentication_policy=bap,
                          root_factory='eos_db.models.RootFactory')

    config.add_subscriber(add_cors_headers_response_callback, NewRequest)

    #Needed to ensure proper 401 responses
    config.add_forbidden_view(basic_challenge(bap))

    settings = config.registry.settings
    server.choose_engine(settings['server'])

    # Top-level home page. Yields API call list?

    config.add_route('home', '/')

    # Test setup calls

    config.add_route('setup', '/setup')
    config.add_route('setup_states', '/setup_states')

    # Session API calls

    config.add_route('sessions', '/sessions') # Get session list
    config.add_route('session', '/session') # Get session details or
                                            # Post new session or
                                            # Delete session

    # User-related API calls

    config.add_route('users', '/users') # Return user list
    config.add_route('user', '/users/{name}')   # Get user details or
                                                        # Put new user or
                                                        # Delete user

    config.add_route('user_touches', '/users/{name}/touches')
                                            # Get server touches

    config.add_route('user_password', '/users/{name}/password')
                                            # Put new password
                                            # Get password verification

    config.add_route('user_credit', '/users/{name}/credit')
                                            # Put new credit or debit
                                            # Get current balance

    # Server-related API calls

    config.add_route('servers', '/servers') # Return server list
    config.add_route('server', '/servers/{name}')    # Get server details or
                                                    # Post new server or
                                                    # Delete server

    config.add_route('server_by_id', '/servers/by_id/{name}')

    # Server state-related calls.

    config.add_route('states', '/states/{name}') # Get list of servers in given state.

    config.add_route('server_start', '/servers/{name}/Starting')
    config.add_route('server_stop', '/servers/{name}/Stopping')

    config.add_route('server_restart', '/servers/{name}/Restarting')

    config.add_route('server_pre_deboost', '/servers/{name}/Pre_Deboosting')
    config.add_route('server_pre_deboosted', '/servers/{name}/Pre_Deboosted')

    config.add_route('server_started', '/servers/{name}/Started')
    config.add_route('server_stopped', '/servers/{name}/Stopped')

    config.add_route('server_prepare', '/servers/{name}/Preparing')
    config.add_route('server_prepared', '/servers/{name}/Prepared')

    config.add_route('server_boost', '/servers/{name}/Boosting')
    config.add_route('server_boosted', '/servers/{name}/Boosted')

    config.add_route('server_state', '/servers/{name}/state')

    config.add_route('server_owner', '/servers/{name}/owner') #


    config.add_route('server_touches', '/servers/{name}/touches')
    config.add_route('server_job_status', '/servers/{name}/job/{job}/status')  # Get server touches

    # Server configuration change calls.

    config.add_route('server_specification','servers/{name}/specification') # Get or put server specification

    config.scan()
    return config.make_wsgi_app()


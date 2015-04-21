""" EOS-DB Init Module.

Contains routing for EOS-DB API, and callbacks for response modification."""

from pyramid.config import Configurator
from pyramid.events import NewRequest, NewResponse
from pyramid.security import authenticated_userid, remember

import logging
import os
import warnings
import eos_db.server

from eos_db.hybridauth import HybridAuthenticationPolicy
from pyramid.httpexceptions import HTTPUnauthorized

# FIXME - when deployed we'll need to call from eoscloud.nerc.ac.uk, but that should be covered
# as being the same origin.  In any case, this shouldn't be hard-coded I'm sure.
ALLOWED_ORIGIN = ('http://localhost:6542',)

def add_cors_headers_response_callback(event): # FIXME - Invalid name (PEP8)
    """ Add response header to enable Cross-Origin Resource Sharing. The
    calling domain is checked against the tuple ALLOWED_ORIGIN, and if it
    matches, then a set of allow headers are sent, allowing the origin, the
    set of methods, and the passing of credentials, which is essential for
    the pass-through token auth which we use for security. """

    def cors_headers(request, response):
        """ Callback for CORS. """

        log = logging.getLogger(__name__)
        if 'Origin' in request.headers:
            origin = request.headers['Origin']
            print ("Origin: " + origin)
            if origin in ALLOWED_ORIGIN:
                log.debug('Access Allowed')
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Methods'] = \
                    'GET, POST, PUT, OPTIONS, DELETE, PATCH'
                response.headers['Access-Control-Allow-Credentials'] = 'true'

    event.request.add_response_callback(cors_headers)

def add_cookie_callback(event):
    """ Add a cookie containing a security token to all response headers from
    eos_db."""

    #Suppress this warning which I already know about.  Note this sets the global
    #warnings filter so it's something of a nasty side-effect.
    warnings.filterwarnings("ignore", r'Behavior of MultiDict\.update\(\) has changed')
    def cookie_callback(request, response):
        """ Cookie callback. """

        if response.status[0] == '2':
            print(remember(request, request.authenticated_userid))
            response.headers.update(remember(request,
                                             request.authenticated_userid))
            print(response.headers)

    event.request.add_response_callback(cookie_callback)

def groupfinder(userid, request):
    """ Return the user group (just one) associated with the userid. This uses a server
    function to check which group a user has been associated with. The mapping
    of groups to capabilities is stored in views.PermissionsMap """

    # FIXME - server not called correctly. Is this even being called?
    # Also groupfinder doesn't use the request argument any more. Can be
    # streamlined.

    group = server.get_user_group(userid)
    if group is not None:
        return ["group:" + str(group[0])]


def passwordcheck():
    """Generates a callback supplied to HybridAuthenticationPolicy to check
       the password. The password check is cached to speed up checking when
       the same user is repeatedly accessing the system, or when the system
       makes multiple password checks for a single request.
    """

    # Bcrypt is slow, which is good to deter dictionary attacks, but bad when
    # the same user is calling multiple API calls, and especially bad for the
    # tests. This one-item cache should be crude but effective:
    lastpass = [""]

    def _passwordcheck(login, password, request):
        """ Password checking callback. """

        print("Checking %s:%s for %s" % (login, password, request))
        print("Lastpass is " + lastpass[0])

        if login == "agent" and password == "sharedsecret":
            return ['group-agents']

        elif (str(lastpass[0]) == login + ":" + password or \
        eos_db.server.check_password(login, password)):

            user_group = eos_db.server.get_user_group(login)[0]

            print("Found user group " + user_group)

            if user_group in ("administrators", "users", "agents"):
                # Remember that this worked
                lastpass[0] = login + ":" + password

                return ['group:' + user_group]
            else:
                lastpass[0] = ""
                return None
        else:
            lastpass[0] = ""
            return None

    return _passwordcheck

#FIXME? main takes global_config as an argument here but why?
def main(global_config, **settings):
    """ Set routes, authentication policies, and add callbacks to modify
    responses."""


    hap = HybridAuthenticationPolicy(check=passwordcheck(),
                                     secret="Spanner", #FIXME
                                     callback=groupfinder,
                                     realm="eos_db")
    config = Configurator(settings=settings,
                          authentication_policy=hap,
                          root_factory='eos_db.views.PermissionsMap')

    config.add_subscriber(add_cors_headers_response_callback, NewRequest)
    config.add_subscriber(add_cookie_callback, NewRequest)

    # Needed to ensure proper 401 responses
    config.add_forbidden_view(hap.get_forbidden_view)

    settings = config.registry.settings
    #FIXME - server again not being called correctly here. Fix the import
    #or the reference below.
    server.choose_engine(settings['server'])

    # Top-level home page. Yields API call list.

    config.add_route('home', '/')

    # FIXME - database setup should be done when the server starts, not as
    # an API call.
    # FIXME2 - remove both these and all calls from the test code
    config.add_route('setup',        '/setup')
    config.add_route('setup_states', '/setup_states')

    # Session API calls
    # FIXME - no longer used because sessions are managed by auth.py
    config.add_route('sessions', '/sessions')   # Get session list
    config.add_route('session', '/session')     # Get session details or
                                                # Post new session or
                                                # Delete session

    # User-related API calls

    config.add_route('users', '/users')        # Return user list
    config.add_route('user',  '/users/{name}')   # Get user details or
                                                 # Put new user or
                                                 # Delete user
    #TODO - I think we need this?  How do i find out who I am?  By querying /session?
    config.add_route('myself', '/user')


    config.add_route('user_touches',  '/users/{name}/touches')
                                            # Get server touches

    config.add_route('user_password', '/users/{name}/password')
                                            # Put new password
                                            # Get password verification by posting
                                            # password=asdf ??  Or not?

    config.add_route('user_credit',   '/users/{name}/credit')
                                            # Put new credit or debit
                                            # Get current balance

    # Server-related API calls

    config.add_route('servers', '/servers')  # Return server list
    config.add_route('server',  '/servers/{name}')  # Get server details or
                                                    # Post new server or
                                                    # Delete server

    config.add_route('server_by_id', '/servers/by_id/{name}')

    # Server state-related calls.

    config.add_route('states', '/states')       # FIXME - Remove.  Really?  Shouldn't this dump out the
                                                # mapping of state->count that I need for my agent controller?
    config.add_route('state',  '/states/{name}') # Get list of servers in
                                                 # the given state.

    # FIXME
    # What do these do?  And if we really need them, can we generate them
    # by looping over server.get_state_list()?
    # Looking at views.py, there is custom logic, so for example if you set
    # a server Boosting it will set up a deboost and also change the credit.
    # But I strongly suspect that Ben's logic is broken here.
    config.add_route('server_start',         '/servers/{name}/Starting')
    config.add_route('server_stop',          '/servers/{name}/Stopping')
    config.add_route('server_restart',       '/servers/{name}/Restarting')
    config.add_route('server_pre_deboost',   '/servers/{name}/Pre_Deboosting')
    config.add_route('server_pre_deboosted', '/servers/{name}/Pre_Deboosted')
    config.add_route('server_started',       '/servers/{name}/Started')
    config.add_route('server_stopped',       '/servers/{name}/Stopped')
    config.add_route('server_prepare',       '/servers/{name}/Preparing')
    config.add_route('server_prepared',      '/servers/{name}/Prepared')
    config.add_route('server_boost',         '/servers/{name}/Boosting')
    config.add_route('server_boosted',       '/servers/{name}/Boosted')
    config.add_route('server_error',         '/servers/{name}/Error')

    config.add_route('server_state',
                     '/servers/{name}/state') # Get or put server state
    config.add_route('server_owner',
                     '/servers/{name}/owner')  # Get or put server ownership
    config.add_route('server_touches',
                     '/servers/{name}/touches') # Get server touches.
    config.add_route('server_job_status',
                     '/servers/{name}/job/{job}/status')  # Get server touches

    # Server configuration change calls.

    config.add_route('server_specification',
                     'servers/{name}/specification')    # Get or put server
                                                       # specification

    config.scan()
    return config.make_wsgi_app()

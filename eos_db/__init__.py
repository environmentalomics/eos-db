""" EOS-DB Init Module.

Contains routing for EOS-DB API, and callbacks for response modification."""

from pyramid.config import Configurator
from pyramid.events import NewRequest, NewResponse
from pyramid.security import authenticated_userid, remember

import logging
import os
import warnings

from eos_db import server
from eos_db.auth import HybridAuthenticationPolicy
from pyramid.httpexceptions import HTTPUnauthorized

# FIXME - when deployed we'll need to call from eoscloud.nerc.ac.uk, but that should be covered
# as being the same origin.  In any case, this shouldn't be hard-coded I'm sure.  Maybe return
# http://localhost:* works?
#ALLOWED_ORIGIN = ('http://localhost:6542',)

log = logging.getLogger(__name__)

def add_cors_callback(event):
    """ Add response header to enable Cross-Origin Resource Sharing. The
    calling domain is checked against the tuple ALLOWED_ORIGIN, and if it
    matches, then a set of allow headers are sent, allowing the origin, the
    set of methods, and the passing of credentials, which is essential for
    the pass-through token auth which we use for security. """

    def cors_headers(request, response):
        """ Callback for CORS. """

        origin = request.headers.get('Origin', 'UNKNOWN')
        log.debug("Origin: " + origin)
        if origin.startswith('http://localhost:'):
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
            #print(remember(request, request.authenticated_userid))
            response.headers.update(remember(request,
                                             request.authenticated_userid))
            #print(response.headers)

    event.request.add_response_callback(cookie_callback)


def passwordcheck(hardcoded=()):
    """Generates a callback supplied to HybridAuthenticationPolicy to check
       the password. The password check is cached to speed up checking when
       the same user is repeatedly accessing the system, or when the system
       makes multiple internal password checks for a single request.
       Any (user,pass,group) triplets passed as hardcoded will be let through
       without querying the database.
    """

    # Bcrypt is slow, which is good to deter dictionary attacks, but bad when
    # the same user is calling multiple API calls, and especially bad for the
    # tests. This one-item cache should be crude but effective.
    # It does mean that if you chage a password the old one will still work until
    # you or someone else logs in.  A workaround is to force a dummy login after
    # a password change.
    # FIXME - I think I can sort this out by caching the credentials in the
    # requast object, which is less hacky.  This cache is nasty.
    lastpass = [""]

    # Dict-ify the hard-coded users.  Normally this will be
    # ('agent', 'secret', 'agents') => {'agent' : ('secret': 'agents')}
    hc = { x[0]: (x[1],x[2]) for x in hardcoded }

    def _passwordcheck(login, password, request):
        """ Password checking callback. """

        #Do not enable these unless you need to test password stuff, as
        #user details will be printed to STDOUT
#         print("Checking %s:%s for %s" % (login, password, request))
#         print("Lastpass is " + lastpass[0])
#         print("Hard-coded users are " + str(tuple(hc.keys())) )

        if login in hc:
            if hc[login][0] == password:
                return ['group:' + hc[login][1]]
            else:
                return None

        elif (str(lastpass[0]) == login + ":" + password or \
            server.check_password(login, password)):

            user_group = server.get_user_group(login)

            log.debug("Found user group " + user_group)

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

def get_secret(settings, secret):
    """ Given the global settings and a name of a secret, determine the secret.
        The secrets we need to function are the 'authtkt' secret which does not need
        to be shared but does need to be stable, and the 'agent' secret which needs
        to be shared with the agents.
        On the production system these must be securely generated at startup.
        On the test system we can use placeholder values, but in either case there
        is no excuse for hard-coding them into the script.

        :params
        :settings dict: settings
        :secret string: name of secret
    """
    #Setting a secretfile in the environment trumps any settings, or
    #else look for a secretfile in the settings.
    secretfile = ( os.environ.get(secret + "_secretfile") or
                   settings.get(secret + ".secretfile") )

    res = None
    if secretfile:
        #If you specify one the file must exist, or an exception will be raised,
        #but there is no check on the actual file contents.
        log.warning("Getting secret from " + secretfile)
        with open(secretfile) as ssfile:
            res = ssfile.read().rstrip('\n')
    else:
        #If a secret is supplied directly, use it.
        res = settings.get(secret + ".secret")

    if not res:
        raise ValueError("The secret cannot be empty.")
    return res


#FIXME? main takes global_config as an argument here but why?
# Also - Is this called just once per initialisation?  Ie. can I generate my
# shared secret here?
def main(global_config, **settings):
    """ Set routes, authentication policies, and add callbacks to modify
    responses."""

    agent_spec = [ ('agent', get_secret(settings, 'agent'), 'agents') ]

    hap = HybridAuthenticationPolicy(check=passwordcheck(hardcoded=agent_spec),
                                     secret=get_secret(settings, "authtkt"),
                                     realm="eos_db")
    config = Configurator(settings=settings,
                          authentication_policy=hap,
                          root_factory='eos_db.views.PermissionsMap')

    config.add_subscriber(add_cors_callback, NewRequest)
    config.add_subscriber(add_cookie_callback, NewRequest)

    # Needed to ensure proper 401 responses
    config.add_forbidden_view(hap.get_forbidden_view)

    # Do this if you need extra info generated by the Configurator, but
    # we do not.
    #settings = config.registry.settings

    # Set the engine, but only if it's not already set.  This is useful
    # for testing where we can re-initialise the webapp while leaving the
    # database in place.
    server.choose_engine(settings['server'], replace=False)

    # Top-level home page. Yields API call list.

    config.add_route('home', '/')

    # FIXME - database setup should be done when the server starts, not as
    # an API call.
    # FIXME2 - remove both these and all calls from the test code
    config.add_route('setup',        '/setup')
    config.add_route('setup_states', '/setup_states')

    # User-related API calls (callable by users)

    config.add_route('users',       '/users')         # Return user list

    config.add_route('my_user',     '/user')          # Return info about me
    config.add_route('my_password', '/user/password') # Set my password
    config.add_route('my_touches',  '/user/touches')  # Get server touches
    config.add_route('my_credit',   '/user/credit')   # Get (but not set!) my credit

    # User-related API calls (callable by Actors/Admins)
    config.add_route('user',  '/users/{name}')   # Get user details or
                                                 # Put new user or
                                                 # Delete user


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

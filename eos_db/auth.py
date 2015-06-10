""" Hybrid Authentication Module - Wraps BasicAuthAuthenticationPolicy and
    AuthTktAuthenticationPolicy to provide an authentication system whereby a
    user can authenticate on any view with Basic Auth, but will then receive a
    cookie with an auth ticket, and be able to use that for subsequent
    requests.

    Basically, with this scheme, every page becomes a login page.  The
    advantage is that scripts can use BasicAuth which is super-siple,
    but templates and JavaScript can use a Cookie which is faster and simpler
    for them.
"""

from pyramid.authentication import (BasicAuthAuthenticationPolicy,
                                    AuthTktAuthenticationPolicy)
from pyramid.httpexceptions import HTTPUnauthorized, HTTPRequestTimeout
from pyramid.security import remember

from eos_db import server

import warnings
import logging
log = logging.getLogger(__name__)


def add_cookie_callback(event):
    """ Add a cookie containing a security token to all response headers.
        This should be added to the configurator as a subscriber in addition to
        setting the authentication_policy.
    """

    #Suppress this warning which I already know about.  Note this sets the global
    #warnings filter so it's something of a nasty side-effect.
    warnings.filterwarnings("ignore", r'Behavior of MultiDict\.update\(\) has changed')
    def cookie_callback(request, response):
        """ Cookie callback. """

        if response.status[0] == '2':
             response.headers.update(remember(request,
                                              request.authenticated_userid))

    event.request.add_response_callback(cookie_callback)

class HybridAuthenticationPolicy():
    """ HybridAuthenticationPolicy. Called in the same way as other auth
        policies, but wraps Basic and AuthTkt.
        This policy also caches password lookups by remembering them in the
        request object.
    """

    def __init__(self, secret, realm='Realm', hardcoded=()):
        """ We need to initialise variables here for both forms of auth which
            we're planning on using.
            :param secret: A hashing secret for AuthTkt, which should be generated outside
                           the Pyhton process.
            :param realm: The Basic Auth realm which is probably set to eos_db.
            :param hardcoded: Triplets of user:password:group that should not be looked
                              up in the database.
        """
        self.hardcoded = { x[0]: (x[1],x[2]) for x in hardcoded }

        #DELETE ME
        #self.check = check   # Password check routine passed to the constructor.
        #self.realm = realm   # Basic Auth realm.

        # Now initialise both Auth Policies. AuthTkt has sha256 specified in
        # place of the default MD5 in order to suppress warnings about
        # security.
        self.bap = BasicAuthAuthenticationPolicy(check=self.passwordcheck,
                                                 realm=realm)
        self.tap = AuthTktAuthenticationPolicy(secret=secret,
                                               callback=self.groupfinder,
                                               cookie_name='auth_tkt',
                                               hashalg='sha256')

    #Utility functions to interact with eos_db.server
    def groupfinder(self, username, request):
        """ Return the user group (just one) associated with the user. This uses a server
            function to check which group a user has been associated with.
            This provides the standard callback wanted by AuthTktAuthenticationPolicy.
            An alternative would be to encode the groups in the Tkt.
            The mapping of groups to actual capabilities is stored in views.PermissionsMap
            """

        group = server.get_user_group(username)
        if group:
            return ["group:" + str(group)]

    def passwordcheck(self, login, password, request):
            """Password checking callback.
            """

            hc = self.hardcoded

            if login in hc and  hc[login][0] == password:
                    return ['group:' + hc[login][1]]

            elif server.check_password(login, password):
                user_group = server.get_user_group(login)
                log.debug("Found user group %s" % user_group)
                return ['group:' + user_group]

            else:
                log.debug("Password chack failed for user %s" % login)
                return None


    def unauthenticated_userid(self, request):
        """ Return the userid parsed from the auth ticket cookie. If this does
            not exist, then check the basic auth header, and return that, if it
            exists.
        """
        #Allow forcing the auth_tkt cookie.  Helpful for JS calls.
        #Maybe move this to a callback so it only ever happens once?
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        #Or, surely:
        return ( self.tap.unauthenticated_userid(request) or
                 self.bap.unauthenticated_userid(request) )

    def authenticated_userid(self, request):
        """ Return the Auth Ticket user ID if that exists. If not, then check
            for a user ID in Basic Auth.
        """
        try:
            return request.cached_authenticated_userid
        except:
            #Proceed to look-up then
            pass

        #Allow forcing the auth_tkt cookie.
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        request.cached_authenticated_userid = ( self.tap.unauthenticated_userid(request) or
                                                self.bap.unauthenticated_userid(request) )
        return request.cached_authenticated_userid

    def effective_principals(self, request):
        """ Returns the list of effective principles from the auth policy
        under which the user is currently authenticated. Auth ticket takes
        precedence. """

        try:
            return request.cached_effective_principals
        except:
            #Proceed to look-up then
            pass

        #Allow forcing the auth_tkt cookie.
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        userid = self.tap.authenticated_userid(request)
        if userid:
            request.cached_effective_principals = self.tap.effective_principals(request)
        else:
            request.cached_effective_principals = self.bap.effective_principals(request)

        return request.cached_effective_principals

    def remember(self, request, principal, **kw):
        """Causes the session info to be remembered by passing the appropriate
           AuthTkt into the response.
        """
        # We always rememeber by creating an AuthTkt, but only if there is something to remember
        # and if the user was not in the hard-coded list.
        if principal and principal not in self.hardcoded:
            return self.tap.remember(request, principal, **kw)
        else:
            return ()

    def forget(self, request):
        """ Forget both sessions. """

        return self.bap.forget(request) + self.tap.forget(request)

    def get_forbidden_view(self, request):
        """ Fire a 401 when authentication needed. """

        # FIXME - this doesn't distinguish between unauthenticated and
        # unauthorized.  Should it?
        if request.headers.get('auth_tkt'):
            return HTTPRequestTimeout()

        #print ("Access Forbidden")
        response = HTTPUnauthorized()
        response.headers.extend(self.bap.forget(request))
        return response


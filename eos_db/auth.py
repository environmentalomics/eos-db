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

from eos_db import server
import bcrypt

#Utility functions to interact with eos_db.server
def groupfinder(userid, request):
    """ Return the user group (just one) associated with the userid. This uses a server
        function to check which group a user has been associated with. The mapping
        of groups to actual capabilities is stored in views.PermissionsMap """

    # FIXME - server not called correctly. Is this even being called?
    # Also groupfinder doesn't use the request argument any more. Can be
    # streamlined?

    group = server.get_user_group(userid)
    if group:
        return ["group:" + str(group)]


class HybridAuthenticationPolicy():
    """ HybridAuthenticationPolicy. Called in the same way as other auth
        policies, but wraps Basic and AuthTkt.
    """

    def __init__(self, check, secret, callback=None, realm='Realm'):
        """ We need to initialise variables here for both forms of auth which
            we're planning on using.
        """
        # This seemed sensible but now I think not:
#         if not secret:
#             secret = bcrypt.gensalt().decode()[7:]
        if not callback:
            callback = groupfinder

        self.check = check   # Password check routine passed to the constructor.
        self.realm = realm   # Basic Auth realm.

        # Now initialise both Auth Policies. AuthTkt has sha256 specified in
        # place of the default MD5 in order to suppress warnings about
        # security.

        self.bap = BasicAuthAuthenticationPolicy(check, realm)
        self.tap = AuthTktAuthenticationPolicy(secret,
                                               callback,
                                               cookie_name='auth_tkt',
                                               hashalg='sha256')

    def unauthenticated_userid(self, request):
        """ Return the userid parsed from the auth ticket cookie. If this does
            not exist, then check the basic auth header, and return that, if it
            exists.
        """
        #Allow forcing the auth_tkt cookie.
        #FIXME - move this to a callback so it only happens once.
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        userid = self.tap.unauthenticated_userid(request)
        if userid:
            #print ("Token UserID: " + userid)
            return userid
        else:
            userid = self.bap.unauthenticated_userid(request)
            if userid:
                #print ("Basicauth UserID: " + userid)
                return userid

        #FIXME
        #Or, surely:
        return ( self.tap.unauthenticated_userid(request) or
                 self.bap.unauthenticated_userid(request) )

    def authenticated_userid(self, request):
        """ Return the Auth Ticket user ID if that exists. If not, then check
            for a user ID in Basic Auth.
        """
        #Allow forcing the auth_tkt cookie.
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        userid = self.tap.authenticated_userid(request)
        #if userid: print ("Token Authd UserID: " + userid)
        if not userid:
            userid = self.bap.authenticated_userid(request)
            #if userid: print ("Basicauth Authd UserID: " + userid)
        return userid

        #FIXME
        #Simplify as above.

    def effective_principals(self, request):
        """ Returns the list of effective principles from the auth policy
        under which the user is currently authenticated. Auth ticket takes
        precedence. """

        #FIXME - I can't see that this will work.  In both cases the principals
        # should be calculated based off authenticated_userid by calling the
        # callback.  Add tests to be sure!

        #Allow forcing the auth_tkt cookie.
        if request.headers.get('auth_tkt'):
            request.cookies['auth_tkt'] = request.headers['auth_tkt']

        #print ("Principals")
        userid = self.tap.authenticated_userid(request)
        #print (userid)
        if userid:
            #print ("Tap")
            #print (str(self.tap.effective_principals(request)))
            return self.tap.effective_principals(request)
        else:
            #print ("Bap")
            return self.bap.effective_principals(request)

    def remember(self, request, principal, **kw):
        """ Remember for Basic Auth is a NOP, so we defer to
            AuthTicket, but only if there is something to remember.
        """
        if principal:
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


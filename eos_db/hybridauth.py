""" Hybrid Authentication Module - Wraps BasicAuthAuthenticationPolicy and
AuthTktAuthenticationPolicy to provide an authentication system whereby a user
can authenticate on any view with Basic Auth, but will then receive a cookie
with an auth ticket, and be able to use that for subsequent requests. """

from pyramid.authentication import (BasicAuthAuthenticationPolicy,
                                    AuthTktAuthenticationPolicy)
from pyramid.httpexceptions import HTTPUnauthorized

class HybridAuthenticationPolicy(): #FIXME - subclass from object
                                    #(best practice).
    """ HybridAuthenticationPolicy. Called in the same way as other auth
    policies, but wraps Basic and AuthTkt."""

    def __init__(self, check, secret, callback, realm='Realm'):
        """ We need to initialise variables here for both forms of auth which
        we're planning on using. """

        self.check = check # Password check routine passed to the constructor.
        self.realm = realm # Basic Auth realm.
        self.secret = secret # Secret used for construction of Auth Ticket.

        # Now initialise both Auth Policies. AuthTkt has sha256 specified in
        # place of the default MD5 in order to improve security, as MD5 has a
        # known hash-collision vulnerability.

        self.bap = BasicAuthAuthenticationPolicy(check, realm)
        self.tap = AuthTktAuthenticationPolicy(secret,
                                               callback,
                                               hashalg='sha256')

    def unauthenticated_userid(self, request):
        """ Return the userid parsed from the auth ticket cookie. If this does
        not exist, then check the basic auth header, and return that, if it
        exists. """

        #print ("Unauth")
        #print (request.headers.raw())
        userid = self.tap.unauthenticated_userid(request)
        if userid:
            #print ("Token UserID: " + userid)
            return userid
        else:
            userid = self.bap.unauthenticated_userid(request)
            if userid:
                #print ("Basicauth UserID: " + userid)
                return userid

    def authenticated_userid(self, request):
        """ Return the Auth Ticket user ID if that exists. If not, then check
        for a user ID in Basic Auth. """

        userid = self.tap.authenticated_userid(request)
        if userid:
            #print ("Token Authd UserID: " + userid)
            pass
        else:
            userid = self.bap.authenticated_userid(request)
            if userid:
                #print ("Basicauth Authd UserID: " + userid)
                pass
        return userid

    def effective_principals(self, request):
        """ Returns the list of effective principles from the auth policy
        under which the user is currently authenticated. Auth ticket takes
        precedence. """

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
        """ Remember for Basic Auth is a NOP, so we specifically ensure that
        details are remembered in the Auth Ticket. """

        return self.tap.remember(request, principal, **kw)

    def forget(self, request):
        """ Forget both sessions. """

        return self.bap.forget(request) + self.tap.forget(request)

    def get_forbidden_view(self, request):
        """Fire a 401 when authentication needed. """

        #print ("Access Forbidden")
        response = HTTPUnauthorized()
        response.headers.extend(self.forget(request))
        return response



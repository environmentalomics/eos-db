from pyramid.authentication import (BasicAuthAuthenticationPolicy,
                                    AuthTktAuthenticationPolicy)
from pyramid.httpexceptions import HTTPUnauthorized

class HybridAuthenticationPolicy():

    def __init__(self, check, secret, realm='Realm'):
        self.check = check
        self.realm = realm
        self.secret = secret

        self.bap = BasicAuthAuthenticationPolicy(check, realm)
        self.tap = AuthTktAuthenticationPolicy(secret)

    def unauthenticated_userid(self, request):
        """ Return the userid parsed from the auth ticket cookie. If this does
        not exist, then check the basic auth header, and return that, if it
        exists. """
        print ("Unauth")
        print (request.headers.raw())
        userid = self.tap.unauthenticated_userid(request)
        if userid:
            print ("Token UserID: " + userid)
            return userid
        else:
            userid = self.bap.unauthenticated_userid(request)
            if userid:
                print ("Basicauth UserID: " + userid)
                return userid

    def authenticated_userid(self, request):
        userid = self.tap.authenticated_userid(request)
        if userid:
            print ("Token Authd UserID: " + userid)
        else:
            userid = self.bap.authenticated_userid(request)
            if userid:
                print ("Basicauth Authd UserID: " + userid)
        return userid

    def effective_principals(self, request):
        print ("Principals")
        userid = self.tap.authenticated_userid(request)
        if userid:
            print ("Tap")
            return self.tap.effective_principals(request)
        else:
            print ("Bap")
            return self.bap.effective_principals(request)

    def remember(self, request, principal, **kw):
        """"""
        print ("Remember " + str(self.tap.remember(request, principal, **kw)))
        return self.tap.remember(request, principal, **kw)

    def forget(self, request):
        """ Forget both sessions. """
        return self.bap.forget(request) + self.tap.forget(request)

    def get_forbidden_view(self, request):
        """Fire a 401 when authentication needed
        """
        print ("Access Forbidden")
        response = HTTPUnauthorized()
        response.headers.extend(self.forget(request))
        return response



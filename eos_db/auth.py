import binascii

from paste.httpheaders import AUTHORIZATION
from paste.httpheaders import WWW_AUTHENTICATE

from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone
from pyramid.security import Authenticated
from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPUnauthorized

from zope.interface import implements

def _get_basicauth_credentials(request):
    authorization = AUTHORIZATION(request.environ)
    try:
        authmeth, auth = authorization.split(' ', 1)
    except ValueError:  # not enough values to unpack
        return None
    if authmeth.lower() == 'basic':
        try:
            auth = auth.strip().decode('base64')
        except binascii.Error:  # can't decode
            return None
        try:
            login, password = auth.split(':', 1)
        except ValueError:  # not enough values to unpack
            return None
        return {'login': login, 'password': password}

    return None

class BasicAuthenticationPolicy(object):
    """An instance of this is passed to pyramid.config.Configurator in __init__.py
       with `check` being a callback to a function that checks passwords against
       the database or the agents shared secret.
    """

    implements(IAuthenticationPolicy)

    def __init__(self, check, realm='eos_db'):
        self.check = check
        self.realm = realm

    def authenticated_userid(self, request):
        credentials = _get_basicauth_credentials(request)
        if credentials is None:
            return None
        userid = credentials['login']
        if self.check(credentials, request) is not None:  # is not None!
            return userid

    def effective_principals(self, request):
        effective_principals = [Everyone]
        credentials = _get_basicauth_credentials(request)
        if credentials is None:
            return effective_principals
        userid = credentials['login']
        groups = self.check(credentials, request)
        if groups is None:  # is None!
            return effective_principals
        effective_principals.append(Authenticated)
        effective_principals.append(userid)
        effective_principals.extend(groups)
        return effective_principals

    def unauthenticated_userid(self, request):
        creds = _get_basicauth_credentials(request)
        if creds is not None:
            return creds['login']
        return None

    def remember(self, request, principal, **kw):
        return []

#     def forget(self, request):
#         head = WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
#         return head

    #Ensure that unauthenticated users get told to log in.
    #Not sure where this really belongs.
    def forbidden_view(self, request, foo):
        resp = HTTPUnauthorized()
        resp.www_authenticate = 'Basic realm="%s"' % self.realm
        return resp

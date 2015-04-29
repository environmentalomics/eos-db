"""Tests the HybridAuth mechanism for authentication.
   See auth.py for an explanation of how this works.
"""
import os
import unittest, requests
from eos_db import server
from webtest import TestApp
from pyramid.paster import get_app

# Depend on test.ini in the same dir as thsi file.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestCookie(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a http server.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)

        # Punch in new administrator account with direct server call

        server.choose_engine("SQLite")  # Sets global var "engine" - in the
                                        # case of SQLite this is a fresh RAM
                                        # DB each time.

        # Create new user. This will implicitly generate the tables.
        id1 = server.create_user(None, "testuser", "testuser", "testuser")
        server.touch_to_add_user_group("testuser", "users")
        server.touch_to_add_password(id1, "testpass")

        id2 = server.create_user(None, "administrator", "administrator", "administrator")
        server.touch_to_add_user_group("administrator", "administrators")
        server.touch_to_add_password(id2, "adminpass")

    """Confirm lack of any cookie without authentication."""
    def test_no_cookie_without_auth(self):
        """ No cookie should be set when calling an endpoint that
            does not require authorization.
        """
        self.app.authorization = None
        r = self.app.get("/", status=200)

        self.assertEqual(r.headers.get('Set-Cookie', 'empty'), 'empty')

        #Equivalently:
        self.assertEqual(self.app.cookies, {})

    def test_no_username(self):
        """ The DB API should return a 401 unauthorised if I submit a request
            with no username / password provided.
            Similar to test_unauthenticated_api but with an extra check that no
            cookie is set.
        """
        self.app.authorization = None
        r = self.app.get("/users/testuser", status=401)

        self.assertEqual(r.headers.get('Set-Cookie', 'empty'), 'empty')


    def test_invalid_username(self):
        """ The DB API should return a 401 unauthorised if I submit a bad
            username / password combination.  And again no cookie
        """
        self.app.authorization = ('Basic', ('invaliduser', 'invalidpassword'))

        r = self.app.get("/users/testuser", status=401)
        self.assertEqual(r.headers.get('Set-Cookie', 'empty'), 'empty')

    """Confirm cookie returned upon authentication."""
    def test_valid_username(self):
        """ The DB API should return a cookie if I submit a correct username
        and password. The cookie should allow me to make a successful request
        using it alone. """

        self.app.authorization = ('Basic', ('testuser', 'testpass'))
        r = self.app.get("/users/testuser", status=200)
        cookie = self.app.cookies['auth_tkt']

        self.app.reset()                         # clear cookie cache
        self.app.authorization = None            # remove auth credentials
        self.app.set_cookie("auth_tkt", cookie)  # set cookie to old value

        r = self.app.get("/users/testuser", status=200)

        #Furthermore, we should still get the same cookie on the second call
        self.assertEqual(self.app.cookies['auth_tkt'], cookie)

    def test_broken_cookie(self):
        """ The DB API should refuse to service a request with a broken cookie. """

        self.app.authorization = ('Basic', ('testuser', 'testpass'))
        r = self.app.get("/users/testuser", status=200)
        cookie = 'I am a fish'

        self.app.reset()                         # clear cookie cache
        self.app.authorization = None            # remove auth credentials
        self.app.set_cookie("auth_tkt", cookie)  # set cookie to bad value
        r = self.app.get("/users/testuser", status=401, expect_errors=False)

    def test_invalid_cookie(self):
        """ The DB API should refuse to service a request with an invalid cookie. """

        self.app.authorization = ('Basic', ('testuser', 'testpass'))
        r = self.app.get("/users/testuser", status=200)
        cookie = '94514a32a7923939584470e8fc01f9b073bc3c8171542c8b7deb0' + \
                 'dd459400945553f9ed9dGVzdHVzZXI%3D!userid_type:b64unicode'

        self.app.reset()                         # clear cookie cache
        self.app.authorization = None            # remove auth credentials
        self.app.set_cookie("auth_tkt", cookie)  # set cookie to bad value
        r = self.app.get("/users/testuser", status=401, expect_errors=False)

if __name__ == '__main__':
    unittest.main()

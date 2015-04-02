"""Tests for DB API behaviour when logged in as administrator

"""
import unittest, requests
from eos_db import server
from webtest import TestApp
# FIXME - do not rely on pyramid.paster for this
from pyramid.paster import get_app

class TestCookie(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a http server.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app('../../test.ini')
        self.app = TestApp(self.appconf)

        # Punch in new administrator account with direct server call

        server.choose_engine("SQLite")  # Sets global var "engine" - in the
                                        # case of SQLite this is a fresh RAM
                                        # DB each time.

        # Create new user. This will implicitly generate the tables.

        server.create_user("user", "testuser", "testuser", "testuser")
        server.touch_to_add_user_group("testuser", "users")
        server.touch_to_add_password(1, "testpass")

        server.create_user("user", "administrator", "administrator", "administrator")
        server.touch_to_add_user_group("administrator", "administrators")
        server.touch_to_add_password(2, "adminpass")

    """Basic API support functions."""

    def test_no_username(self):
        """ The DB API should return a 401 unauthorised if I submit a request 
        with no username / password provided. """
        self.app.authorization = None
        r = self.app.get("/users/johndoe/password", status=401, expect_errors=False)

    def test_invalid_username(self):
        """ The DB API should return a 401 unauthorised if I submit a bad 
        username / password combination. """
        self.app.authorization = ('Basic', ('invaliduser', 'invalidpassword'))
        r = self.app.get("/users/johndoe/password", status=401, expect_errors=False)

    def test_valid_username(self):
        """ The DB API should return a cookie if I submit a correct username
        and password. The cookie should allow me to make a successful request
        using it alone. """

        print ("Start test...")
        self.app.authorization = ('Basic', ('testuser', 'testpass'))
        r = self.app.get("/users/testuser", status=200, expect_errors=False)
        cookie = self.app.cookies['auth_tkt']
        print ("Cookie: " + cookie)
        print ("Resetting session...")
        self.app.reset()  # clear cookie cache
        self.app.authorization = None  # remove auth credentials
        self.app.set_cookie("auth_tkt", cookie)  # set cookie to old value
        print ("Making request...")
        r = self.app.get("/users/testuser", status=200, expect_errors=False)

    def test_broken_cookie(self):
        """ The DB API should refuse to service a request with a broken cookie. """

        print ("Start test...")
        self.app.authorization = ('Basic', ('testuser', 'testpass'))
        r = self.app.get("/users/testuser", status=200, expect_errors=False)
        cookie = 'ca32e31f7b9ed0157ed645911880309d7s809d1fb80dc207f41d2' + \
        'a14a88e0d77e328f8e56410b0b195e4dd4824e7d1acb1dbe412b041ce7aae3' + \
        '88f72b8ac747b551bc59adGVzdHVzZXI%3D!userid_type:b64unicode'
        self.app.reset()  # clear cookie cache
        self.app.authorization = None  # remove auth credentials
        r = self.app.get("/users/testuser", headers={'auth_tkt': cookie}, status=401, expect_errors=False)

if __name__ == '__main__':
    unittest.main()

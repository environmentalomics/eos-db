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

        # Switch to API basic auth with created account
        self.app.authorization = ('Basic', ('administrator', 'adminpass'))

        # Create admin user. This will implicitly generate the tables.

        server.create_user("user", "administrator", "administrator", "administrator")
        server.touch_to_add_user_group("administrator", "administrators")
        server.touch_to_add_password(1, "adminpass")

        response = self.app.post('/setup_states')

    """Basic API support functions."""

    def test_no_username(self):
        """ The DB API should return a 401 unauthorised if I submit a request 
        with no username / password provided. """

    def test_invalid_username(self):
        """ The DB API should return a 401 unauthorised if I submit a bad 
        username / password combination. """


    def test_valid_username(self):
        """ The DB API should return a cookie if I submit a correct username /
        password combination. """


    def test_return_cookie(self):
        """ The DB API should return identical results when authenticating
        with a cookie rather than with a basicauth user/pass combo."""


if __name__ == '__main__':
    unittest.main()

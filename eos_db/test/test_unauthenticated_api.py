"""Tests for what eos_db says when user does not authenticate.

   $ ~/eoscloud-venv/bin/python3 -m unittest eos_db.test.test_unauthenticated_api
"""

import unittest
import os
from webtest import TestApp
# Note that pyramid.paster does work in Py3, since PasteDeploy
# is ported, though most of Paste is not.
from pyramid.paster import get_app
from http.cookiejar import DefaultCookiePolicy

from eos_db import server

# Normally I'd frown upon any code that discovers it's own location, but in this
# case it makes sense to use test.ini from the same folder as the test module.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestUnAuth(unittest.TestCase):
    """Tests to see that the server responds as expected to non-authorized requests.
    """
    def setUp(self):
        """Launch pserve/waitress using webtest with test settings.
           Fresh for every test, though it shouldn't matter.
        """
        self.myapp = get_app(test_ini)
        self.testapp = TestApp(self.myapp)

        #No auth, no cookies
        #app.authorization = ('Basic', ('user', 'password'))
        self.testapp.cookiejar.set_policy(DefaultCookiePolicy(allowed_domains=[]))

        #Do this because the authentication system needs to look at the user tables.
        server.deploy_tables()

    def test_nosetup(self):
        """Does the API refuse to set up the database?
        """
        app = self.testapp

        response = app.post('/setup', status=403, expect_errors=True)
        response = app.post('/setup_states', status=403, expect_errors=True)


    def test_homepage(self):
        """Does the home page of the API still work without login
        """
        app = self.testapp
        response = app.get('/', status=200)

        self.assertEqual(response.json['Valid API Call List']['servers'], '/servers')

    def test_servers(self):
        """If I ask for a list of servers, I should get back a 401 code telling me
           to log in.
        """
        app = self.testapp

        response = app.get('/servers', status=401)
        self.assertEqual(response.headers.get('WWW-Authenticate', 'empty'), 'Basic realm="eos_db"')

    def test_get_user(self):
        """If I ask for info on a user, I should get a login challenge regardless of whether that
           user exists.
        """
        app = self.testapp
        self.create_user("foo")

        response = app.get('/users/foo', status=401)
        self.assertEqual(response.headers.get('WWW-Authenticate', 'empty'), 'Basic realm="eos_db"')

        response = app.get('/users/bar', status=401)
        self.assertEqual(response.headers.get('WWW-Authenticate', 'empty'), 'Basic realm="eos_db"')

    def test_servers_baduser(self):
        """If I ask for a list of servers, and give a wrong username+password, I
           should get back a 403
        """

        app = self.testapp
        app.authorization = ('Basic', ('baduser', 'badpassword'))

        response = app.get('/servers', status=401)
        self.assertEqual(response.headers.get('WWW-Authenticate', 'empty'), 'Basic realm="eos_db"')

    def test_servers_badpass(self):
        """Likewise if I give a valid user name but no password
        """
        user_id = server.create_user("administrators", "administrator", "administrator", "administrator")
        #server.touch_to_add_user_group("administrator", "administrators")
        server.touch_to_add_password(user_id, "adminpass")

        app = self.testapp
        app.authorization = ('Basic', ('administrator', 'badpassword'))

        response = app.get('/servers', status=401)

        self.assertEqual(response.headers.get('WWW-Authenticate', 'empty'), 'Basic realm="eos_db"')

    def test_homepage_post(self):
        """Post to home page returns a 404 not found, as no endpoint is
           defined for a POST to this URL.
           #FIXME - should really return a 405??
        """
        app = TestApp(self.myapp)

        response = app.post('/', status=404, expect_errors=True)

###############################################################################
# Support Functions, calling the server code directly                         #
###############################################################################

    def create_user(self, name):
        #Since we are not logged in as the administrator, do this directly
        return server.create_user("users", name + "@example.com", name + " " + name, name)



if __name__ == '__main__':
    unittest.main()

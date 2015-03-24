"""Tests for what eos_db says when user does not autenticate.

"""

import unittest
from webtest import TestApp
# FIXME - do not rely on pyramid.paster for this
from pyramid.paster import get_app

class TestUnAuth(unittest.TestCase):
    """Tests to see that the server responds as expected to non-authorized requests.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.myapp = get_app('../../test.ini')
        self.testapp = TestApp(self.myapp)

        #No auth
        #app.authorization = ('Basic', ('user', 'password'))

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

    def test_homepage_post(self):
        """Post to home page returns a 404 not found
           ?? Is that right ??
        """
        app = TestApp(self.myapp)

        response = app.post('/', status=404, expect_errors=True)


if __name__ == '__main__':
    unittest.main()

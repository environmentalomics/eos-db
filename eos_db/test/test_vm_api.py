"""Tests for VM actions - start, stop, suspend.

"""

import unittest
from webtest import TestApp
# FIXME - do not rely on pyramid.paster for this
from pyramid.paster import get_app

class TestVMAPI(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a http server.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app('../../test.ini')
        self.myapp = TestApp(self.appconf)
        app = self.myapp

        # At this point I need to authenticate as administrator:asdf,
        # but really I should be able to supply a username and password in
        # the line above.
        app.authorization = ('Basic', ('administrator', 'asdf'))

        #Note the response is checked for you.
        response = app.post('/setup', )
        response = app.post('/setup_states')

    def test_environment(self):
        """Does the home page of the API return 200 OK on get?
        """
        app = self.myapp
        response = app.get('/', status=200)

    def test_list_users(self):
        """As an admin I should be able to list the users
        """
        app = self.myapp

        response = app.get('/users', status=200)

        print(response.json)

    def test_start_server(self):
        """Tests the results of calling API to start a server.
        """
        app = self.myapp

        response = app.post_json('/servers/register',
                                 dict(id=1, value='value'))
        response = app.post_json('/servers/asdf/start',
                            dict(id=1, value='value'))
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")

    def test_stop_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = self.myapp

        response = app.post('/servers/register')
        response = app.post('/servers/asdfasdf/start')
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")



if __name__ == '__main__':
    unittest.main()

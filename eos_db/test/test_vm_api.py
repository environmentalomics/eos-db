"""Tests for VM actions - start, stop, suspend.

"""

import unittest
from webtest import TestApp
from pyramid.paster import get_app

class TestVMAPI(unittest.TestCase):
    """Tests API functions associated with VM actions.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.myapp = get_app('../../test.ini')
        app = TestApp(self.myapp)
        response = app.post('/setup')
        assert(response.status=='200 OK')
        response = app.post('/setup_states')
        assert(response.status=='200 OK')

    def test_environment(self):
        """Does the home page of the API return 200 OK on get?
        """
        app = TestApp(self.myapp)
        response = app.get('/')
        assert(response.status=='200 OK')

    def test_start_server(self):
        """Tests the results of calling API to start a server.
        """
        app = TestApp(self.myapp)
        response = app.post_json('/servers/register',
                                 dict(id=1, value='value'))
        response = app.post_json('/servers/asdf/start',
                            dict(id=1, value='value'))
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")

    def test_stop_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/servers/register')
        response = app.post('/servers/asdfasdf/start')
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")

    def test_prestart_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")

    def test_prestop_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")

    def test_preboost_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")

    def test_boost_server(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")

    def test_add_specification(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")

    def test_read_specification(self):
        """Tests the results of calling API to stop a server.
        """
        app = TestApp(self.myapp)
        response = app.post('/')
        response = app.post('/')
        assert(response.text=="Started")


if __name__ == '__main__':
    unittest.main()

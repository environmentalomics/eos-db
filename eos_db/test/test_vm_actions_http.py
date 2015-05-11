"""Tests for VM actions called via WebTest

   $ ~/eoscloud-venv/bin/python3 -m unittest eos_db.test.test_vm_actions_http
"""
import os
import unittest
from eos_db import server
from webtest import TestApp
from pyramid.paster import get_app
from http.cookiejar import DefaultCookiePolicy

# Hmmmmm
STATES_TO_TEST = [
            'Starting',
            'Stopping',
            'Restarting',
            'Pre_Deboosting',
            'Pre_Deboosted',
            'Started',
            'Stopped',
            'Preparing',
            'Prepared', ]
#             'Boosting']

# Depend on test.ini in the same dir as this file.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestVMActionsHTTP(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a HTTP server,
       but we do communicate HTTP requests and responses.
       Outside of setUp, all calls to the database should be via the HTTP API.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)

        #For speed, allow cookie setting.
        # self.app.cookiejar.set_policy(DefaultCookiePolicy(allowed_domains=[]))

        # This sets global var "engine" - in the case of SQLite this is a fresh RAM
        # DB each time.  If we only did this on class instantiation the database would
        # be dirty and one test could influence another.
        # TODO - add a test that tests this.
        server.choose_engine("SQLite")

        # Punch in new administrator account with direct server call
        # This will implicitly generate the tables.
        user_id = server.create_user("administrators", "administrator", "administrator", "administrator")
        #server.touch_to_add_user_group("administrator", "administrators")
        server.touch_to_add_password(user_id, "adminpass")

        self.app.authorization = ('Basic', ('administrator', 'adminpass'))

        # This both sets up the database and sorts out the auth token
        self.app.post('/setup_states')
        self.app.authorization = None

    """VM-related API functions."""

    def test_create_own_retrieve_servers(self):  # FIX
        """ Create a server. Ensure that a 200 OK response results.
        Add an owner to a server. Ensure that a 200 OK response results.
        A user can request a list of servers that they own. An
        administrator can list all the servers. """

        # Create user and server

        self.create_user("testuser")
        self.create_server("testserver")

        # Add ownership

        response = self.app.put('/servers/testserver/owner',
                                {'artifact_id': 'testserver',
                                'actor_id': 'bcollier'})

        # Get server

        response = self.app.get('/servers/testserver',
                                {'hostname': 'testserver'})

        # Get server ownership - !! Not implemented
#
#         response = self.app.get('/servers/testserver/owner',
#                                 {'artifact_id': 'testserver'})

    """ Server State-Change Functions. """

    def test_server_states(self):  # FIX
        """ Check that a server appears in various states after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

        # Create server
        self.create_server("testserver")

        def get_state():
            response = self.app.get('/servers/testserver/state',
                            {'artifact_id': 'testserver'})
            return response.json

        #This should fail because not all the states are valid.
        for state in STATES_TO_TEST:
            res = self.app.post('/servers/testserver/' + state)
            #print("Push result = " + str(res))
            self.assertEqual(get_state(), state)

    def test_retrieve_server(self):
        """ Pull back details of our server by name. """

        self.create_server("testserver")  # Create server

        # Retrieve server details

        response = self.app.get('/servers/testserver',
                                {'hostname': 'testserver'})

    def test_retrieve_server_by_id(self):
        """ Our server will have ID 1. Check that we can retrieve details of
        it."""

        self.create_server("testserver")  # Create server

        # Retrieve server details by name

        response = self.app.get('/servers/by_id/1')

#     def test_update_server(self):
#         """ Not currently implemented. """
#
#         self.create_server("testserver")  # Create server

        # Update server details

        # Check server details

#     def test_delete_server(self):
#         """ Not currently implemented. """


    def test_set_get_server_specification(self):
        """ Follows hard-coded rules for machine behaviour.
        Set machine CPUs to 2. Check, should pass.
        Set machine CPUs to 65000. Check, should fail.
        Set machine RAM to 16. Check, should pass.
        Set machine RAM to 65000. Check, should fail.
        Check that machine RAM and Cores are 2 and 16 as above. """

        self.create_server("testserver")  # Create server

        # Set server spec

        response = self.app.post('/servers/testserver/specification',
                                {'name': 'testserver',
                                 'cores': 2,
                                 'ram': 16 },
                                status=200,
                                expect_errors=False)

        response = self.app.post('/servers/testserver/specification',
                                {'name': 'testserver',
                                 'cores': 65000,
                                 'ram': 65000 },
                                status=400,
                                expect_errors=False)

        # Get server spec

        response = self.app.get('/servers/testserver/specification',
                                {'hostname': 'testserver'},
                                status=200,
                                expect_errors=False)

    def test_retrieve_servers_by_state(self):
        """ The agents need to find out about servers to be acted on.
        """
        app = self.app
        self.create_server("testserver1")
        self.create_server("testserver2")

        app.post('/servers/testserver1/Stopping')
        app.post('/servers/testserver2/Stopping')

        res = app.get('/states/Stopping')

        self.assertEqual(res.json,
                [{"artifact_id":1, "artifact_uuid":"testserver1", "artifact_name":"testserver1"},
                 {"artifact_id":2, "artifact_uuid":"testserver2", "artifact_name":"testserver2"}]
                )

    def test_retrieve_job_progress(self):
        """ Not currently implemented. """

    def test_retrieve_server_touches(self):
        """ Not currently implemented. """

###############################################################################
# Support Functions, calling server admin views                               #
###############################################################################

    def create_user(self, name):
        response = self.app.put('/users/' + name,
                                {'type': 'users',
                                'handle': name + '@example.com',
                                'name': name + " " + name,
                                'username': name},
                                status=200,
                                expect_errors=False)

    def create_server(self, name):
        response = self.app.put('/servers/' + name,
                                {'hostname': name,
                                 'uuid': name },
                                status=200,
                                expect_errors=False)


if __name__ == '__main__':
    unittest.main()

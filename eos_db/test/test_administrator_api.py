"""Tests for DB API behaviour when logged in as administrator

"""

import unittest, json
from eos_db import server
from webtest import TestApp
# FIXME - do not rely on pyramid.paster for this
from pyramid.paster import get_app

STATE_LIST = ['Starting',
            'Stopping',
            'Restarting',
            'Pre_Deboosting',
            'Pre_Deboosted',
            'Started',
            'Stopped',
            'Preparing',
            'Prepared',
            'Boosting']

class TestVMAPI(unittest.TestCase):
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

    def test_home_view(self):
        """ Home view should respond with 200 OK. """
        response = self.app.get('/', status=200, expect_errors=False)

    """User API functions.

    The user functions in the API are primarily used by system utilities.
    Creating a user and password, and validating against the database in
    order to receive an access token, are prerequisites for using functions
    in later sections of the API. These can only be called by an
    administrator."""

    def test_create_retrieve_user(self):
        """ Creating a user should respond with 200 OK.
        Retrieving the user should respond likewise. """

        self.create_user("testuser")

        response = self.app.get('/users/testuser?actor_id=testuser',
                                status=200,
                                expect_errors=False)

    def test_retrieve_users(self):
        """ Add another user. Two records should be returned.

        !! Not implemented. """

        self.create_user("testuser")
        self.create_user("testuser2")

        response = self.app.get('/users', status=501, expect_errors=False)

    def test_update_user(self):
        """ Updating a user. Retrieve details. The results should reflect the
        change.

        !! Not implemented."""

        self.create_user("testuser")

        response = self.app.patch('/users/testuser',
                                  {'type': 'user',
                                  'handle': 'testuser',
                                  'name': 'Test User Updated',
                                  'username':'testuser'},
                                  status=501,
                                  expect_errors=False)

        response = self.app.get('/users/testuser?actor_id=testuser',
                                status=200,
                                expect_errors=False)

    def test_delete_user(self):
        """ Delete a user. Attempt to retrieve details should return 404.

        !! Not implemented."""
        self.create_user("testuser")

        response = self.app.delete('/users/testuser2',
                                   status=501,
                                   expect_errors=False)


    def test_create_check_user_password(self): # FIX
        """ Apply a password to a user. Check that we receive a 200 OK.
        Validate against the database with the user and password above.
        We should receive an access token."""

        self.create_user("testuser")

        response = self.app.put('/users/testuser/password',
                                {'actor_id': 'testuser',
                                'password': 'testpass'},
                                status=200,
                                expect_errors=False)
        response = self.app.get('/users/testuser/password?actor_id=testuser&password=testpass',
                                status=200,
                                expect_errors=False)

    def test_retrieve_user_touches(self):
        """ Retrieve a list of touches that the user has made to the database.
        This can only be requested by the user themselves, an agent or an
        administrator.

        !! Not implemented."""

    def test_create_retrieve_user_credit(self):
        """ Add credit to a user's account. This can only be done by an
        administrator."""

        self.create_user("testuser")

        response = self.app.post('/users/testuser/credit',
                                {'actor_id': 'testuser',
                                'credit': 1000},
                                status=200,
                                expect_errors=False)
        response = self.app.get('/users/testuser/credit',
                                {'actor_id': 'testuser'},
                                status=200,
                                expect_errors=False)
        assert json.loads(json.loads(response.text))['credit_balance'] == 1000 #?? double encoded

    def test_create_own_retrieve_servers(self): #FIX
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
                                'actor_id': 'bcollier'},
                                status=200,
                                expect_errors=False)

        # Get server

        response = self.app.get('/servers/testserver',
                                {'hostname': 'testserver'},
                                status=200,
                                expect_errors=False)

        # Get server ownership - !! Not implemented

        response = self.app.get('/servers/testserver/owner',
                                {'artifact_id': 'testserver'},
                                status=501,
                                expect_errors=False)

        assert json.loads(json.loads(response.text))['credit_balance'] == 1000 #?? double encoded

    """ Server State-Change Functions. """

    def test_server_states(self): #FIX
        """ Check that a server appears in various states after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

        def push_to_state(state):
            response = self.app.post('/servers/testserver/'+state,
                            {'vm_id': 'testserver',
                             'eos_token': 'TOKEN'},
                            status=200,
                            expect_errors=False)

        def get_state():
            response = self.app.get('/servers/testserver/state',
                            {'artifact_id': 'testserver'},
                            status=200,
                            expect_errors=False)
            return response.text

        # Create server

        self.create_server("testserver")

        for state in STATE_LIST:
            push_to_state(state)
            current_state = get_state()
            assert current_state == state
            print current_state

    def test_retrieve_server(self):
        """ Pull back details of our server by name. """

        self.create_server("testserver") # Create server

        # Retrieve server details

        response = self.app.get('/servers/testserver',
                                {'hostname': 'testserver'},
                                status=200,
                                expect_errors=False)

    def test_retrieve_server_by_id(self):
        """ Our server will have ID 1. Check that we can retrieve details of
        it."""

        self.create_server("testserver") # Create server

        # Retrieve server details by name

        response = self.app.get('/server_by_id/1',
                                status=200,
                                expect_errors=False)

    def test_update_server(self):
        """ Not currently implemented. """

        self.create_server("testserver") # Create server

        # Update server details

        # Check server details

    def test_delete_server(self):
        """ Not currently implemented. """

    def test_set_get_server_specification(self):
        """ Follows hard-coded rules for machine behaviour.
        Set machine CPUs to 2. Check, should pass.
        Set machine CPUs to 65000. Check, should fail.
        Set machine RAM to 16. Check, should pass.
        Set machine RAM to 65000. Check, should fail.
        Check that machine RAM and Cores are 2 and 16 as above. """

        self.create_server("testserver") # Create server

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

    def test_retrieve_job_progress(self):
        """ Not currently implemented. """

    def test_retrieve_server_touches(self):
        """ Not currently implemented. """

###############################################################################
#                                                                             #
# Support Functions                                                           #
#                                                                             #
###############################################################################

    def create_user(self, name):
        response = self.app.put('/users/'+name,
                                {'type': name,
                                'handle': name,
                                'name': name,
                                'username': name},
                                status=200,
                                expect_errors=False)

    def create_server(self, name):
        response = self.app.put('/servers/'+name,
                                {'hostname': name,
                                 'uuid': name },
                                status=200,
                                expect_errors=False)

if __name__ == '__main__':
    unittest.main()

"""Tests for DB API behaviour when logged in as user.

"""
import os
import unittest
from webtest import TestApp
# FIXME - do not rely on pyramid.paster for this
from pyramid.paster import get_app

# Depend on test.ini in the same dir as thsi file.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestVMAPI(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a http server.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)
        self.app.authorization = ('Basic', ('administrator', 'asdf'))

        response = self.app.post('/setup', )
        response = self.app.post('/setup_states')


        #setup()             # Deploy tables
        #setup_states()      # Populate states

        # Authentication will use a specialised test account that we will poke
        # into the database. We'll then instruct webtest to use it. It will act
        # as an administrator for the purposes of authorisation.
        # ---->poke in here

        # Note the response is checked for you.
        #

    """Basic API support functions."""

    def test_home_view(self):
        """ Home view should respond with 200 OK. """
        response = self.app.get('/', status=200, expect_errors=False)

    def test_options(self):
        """ Options should respond with 200 OK. """
        response = self.app.options('/', status=200, expect_errors=False)

    """User API functions.

    The user functions in the API are primarily used by system utilities.
    Creating a user and password, and validating against the database in
    order to receive an access token, are prerequisites for using functions
    in later sections of the API. These can only be called by an
    administrator."""

    def test_create_retrieve_user(self):
        """ Creating a user should respond with 200 OK.
        Retrieving the user should respond likewise. """
        response = self.app.put('/users/testuser',
                                {'type': 'values',
                                'handle': 'testuser',
                                'name': 'Test User',
                                'username':'testuser'},
                                status=200,
                                expect_errors=False)
        response = self.app.get('/users/testuser?actor_id=testuser',
                                status=200,
                                expect_errors=False)

    def test_retrieve_users(self):
        """ Add another user. Two records should be returned. """
        response = self.app.put('/users/testuser',
                                {'type': 'user',
                                'handle': 'testuser',
                                'name': 'Test User',
                                'username':'testuser'},
                                 status=200,
                                 expect_errors=False)
        response = self.app.put('/users/testuser2',
                                {'type': 'user',
                                'handle': 'testuser2',
                                'name': 'Test User 2',
                                'username':'testuser2'},
                                status=200,
                                expect_errors=False)
        response = self.app.get('/users/', status=200, expect_errors=False)

    def test_update_user(self):
        """ Updating a user. Retrieve details. The results should reflect the
        change. """
        response = self.app.put('/users/testuser',
                                {'type': 'user',
                                'handle': 'testuser',
                                'name': 'Test User',
                                'username':'testuser'},
                                status=200,
                                expect_errors=False)
        response = self.app.patch('/users/testuser',
                                  {'type': 'user',
                                  'handle': 'testuser',
                                  'name': 'Test User Updated',
                                  'username':'testuser'},
                                  status=200,
                                  expect_errors=False)
        response = self.app.get('/users/testuser?actor_id=testuser',
                                status=200,
                                expect_errors=False)

    def test_delete_user(self):
        """ Delete a user. Attempt to retrieve details should return 404. """
        response = self.app.put('/users/testuser',
                                {'type': 'user',
                                'handle': 'testuser',
                                'name': 'Test User',
                                'username':'testuser'},
                                status=200,
                                expect_errors=False)
        response = self.app.delete('/users/testuser2',
                                   status=200,
                                   expect_errors=False)


    def test_create_check_user_password(self):
        """ Apply a password to our user. Check that we receive a 200 OK.
        Validate against the database with the user and password above.
        We should receive an access token."""

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
        administrator. """

    def test_create_user_credit(self):
        """ Add credit to a user's account. This can only be done by an
        administrator."""

    def test_retrieve_user_credit(self):
        """ A user can request the amount of credit that they have on account.
        """

    def test_retrieve_servers(self):
        """ A user can request a list of servers that they own. An
        administrator can list all the servers. """

    def test_create_server(self):
        """ Create a server. Ensure that a 200 OK response results. """

    def test_create_server_owner(self):
        """ Add an owner to a server. Ensure that a 200 OK response results.
        """

    """ Server State-Change Functions. """

    def test_retrieve_servers_in_state(self):
        """ 200 OK from this call for all legal states."""

    def test_start_server(self):
        """ Check that a server appears in state 'Started' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_restart_server(self):
        """ Check that a server appears in state 'Restarted' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_stop_server(self):
        """ Check that a server appears in state 'Stopped' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_prepare_server(self):
        """ Check that a server appears in state 'Prepared' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_pre_deboost_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_boost_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_stopped_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_started_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_prepared_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_predeboosted_server(self):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_retrieve_server(self):
        """ Pull back details of our server by name. """

    def test_retrieve_server_by_id(self):
        """ Our server will have ID 1. Check that we can retrieve details of
        it."""

    def test_update_server(self):
        """ Not currently implemented. """

    def test_delete_server(self):
        """ Not currently implemented. """

    def test_set_server_specification(self):
        """ Follows hard-coded rules for machine behaviour.
        Set machine CPUs to 2. Check, should pass.
        Set machine CPUs to 65000. Check, should fail.
        Set machine RAM to 16. Check, should pass.
        Set machine RAM to 65000. Check, should fail."""

    def test_get_server_specification(self):
        """ Check that machine RAM and Cores are 2 and 16 as above. """

    def test_retrieve_job_progress(self):
        """ Not currently implemented. """

    def test_retrieve_server_touches(self):
        """ Not currently implemented. """

if __name__ == '__main__':
    unittest.main()

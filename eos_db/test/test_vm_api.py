"""Tests for V

"""
import os
import unittest
from webtest import TestApp
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
        self.myapp = TestApp(self.appconf)
        app = self.myapp

        setup()             # Deploy tables
        setup_states()      # Populate states

        # Authentication will use a specialised test account that we will poke
        # into the database. We'll then instruct webtest to use it. It will act
        # as an administrator for the purposes of authorisation.
        # ---->poke in here
        app.authorization = ('Basic', ('administrator', 'asdf'))

        # Note the response is checked for you.
        response = app.post('/setup', )
        response = app.post('/setup_states')

    """Basic API support functions."""

    def test_home_view(request):
        """ Home view should respond with 200 OK. """

    def test_options(request):
        """ Options should respond with 200 OK. """

    """User API functions.

    The user functions in the API are primarily used by system utilities.
    Creating a user and password, and validating against the database in
    order to receive an access token, are prerequisites for using functions
    in later sections of the API. These can only be called by an
    administrator."""

    def test_create_user(request):
        """ Creating a user should respond with 200 OK. """

    def test_retrieve_user(request):
        """ Retrieving a user should retrieve the results specified above. """

    def test_retrieve_users(request):
        """ Add another user. Two records should be returned. """

    def test_update_user(request):
        """ Updating a user. Retrieve details. The results should reflect the
        change. """

    def test_delete_user(request):
        """ Delete a user. Attempt to retrieve details should return 404. """

    def test_create_user_password(request):
        """ Apply a password to our user. Check that we receive a 200 OK. """

    def test_retrieve_user_password(request):
        """ Validate against the database with the user and password above.
        We should receive an access token. """

    """ User account details and administration.

    These functions are used to retrieve administrative information about a
    user."""

    def test_retrieve_user_touches(request):
        """ Retrieve a list of touches that the user has made to the database.
        This can only be requested by the user themselves, an agent or an
        administrator. """

    def test_create_user_credit(request):
        """ Add credit to a user's account. This can only be done by an
        administrator."""

    def test_retrieve_user_credit(request):
        """ A user can request the amount of credit that they have on account.
        """

    def test_retrieve_servers(request):
        """ A user can request a list of servers that they own. An
        administrator can list all the servers. """

    def test_create_server(request):
        """ Create a server. Ensure that a 200 OK response results. """

    def test_create_server_owner(request):
        """ Add an owner to a server. Ensure that a 200 OK response results.
        """

    """ Server State-Change Functions. """

    def test_retrieve_servers_in_state(request):
        """ 200 OK from this call for all legal states."""

    def test_start_server(request):
        """ Check that a server appears in state 'Started' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_restart_server(request):
        """ Check that a server appears in state 'Restarted' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_stop_server(request):
        """ Check that a server appears in state 'Stopped' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_prepare_server(request):
        """ Check that a server appears in state 'Prepared' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_pre_deboost_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_boost_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_stopped_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_started_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_prepared_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_predeboosted_server(request):
        """ Check that a server appears in relevant state after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """

    def test_retrieve_server(request):
        """ Pull back details of our server by name. """

    def test_retrieve_server_by_id(request):
        """ Our server will have ID 1. Check that we can retrieve details of
        it."""

    def test_update_server(request):
        """ Not currently implemented. """

    def test_delete_server(request):
        """ Not currently implemented. """

    def test_set_server_specification(request):
        """ Follows hard-coded rules for machine behaviour.
        Set machine CPUs to 2. Check, should pass.
        Set machine CPUs to 65000. Check, should fail.
        Set machine RAM to 16. Check, should pass.
        Set machine RAM to 65000. Check, should fail."""

    def test_get_server_specification(request):
        """ Check that machine RAM and Cores are 2 and 16 as above. """

    def test_retrieve_job_progress(request):
        """ Not currently implemented. """

    def test_retrieve_server_touches(request):
        """ Not currently implemented. """

if __name__ == '__main__':
    unittest.main()


"""Old tests:


    def test_environment(self):
        app = self.myapp
        response = app.get('/', status=200)

    def test_list_users(self):
        app = self.myapp

        response = app.get('/users', status=200)

        print(response.json)

    def test_start_server(self):
        app = self.myapp

        response = app.post_json('/servers/register',
                                 dict(id=1, value='value'))
        response = app.post_json('/servers/asdf/start',
                            dict(id=1, value='value'))
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")

    def test_stop_server(self):
        app = self.myapp

        response = app.post('/servers/register')
        response = app.post('/servers/asdfasdf/start')
        response = app.get('/servers/asdasd/state')
        assert(response.text=="Started")

"""

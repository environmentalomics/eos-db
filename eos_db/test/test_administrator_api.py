"""Tests for DB API behaviour when logged in as administrator

   $ ~/eoscloud-venv/bin/python3 -m unittest eos_db.test.test_administrator_api
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

class TestAdminAPI(unittest.TestCase):
    """Tests API functions associated with VM actions.
       Note that all tests are in-process, we don't actually start a HTTP server,
       but we do communicate HTTP requests and responses.
       Outside of setUp, all calls to the database should be via the HTTP API.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)

        #This seems to be how we suppress cookies being remembered.
        #All auth via BasicAuth - never return the session cookie.
        self.app.cookiejar.set_policy(DefaultCookiePolicy(allowed_domains=[]))

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

        # Don't need this for all tests.
        #self.app.post('/setup_states')

    """Unauthenticated API functions."""

    def test_home_view(self):
        """ Home view should respond with 200 OK, as anyone can call it. """
        response = self.app.get('/', status=200)

    """Admin API functions.

    The admin functions in the API are primarily used by system utilities.
    Creating a user and password, and validating against the database in
    order to receive an access token, are prerequisites for using functions
    in later sections of the API. These can only be called by an
    administrator."""

    def test_create_user(self):
        """ Creating a user should respond with 200 OK.
        Retrieving the user should respond likewise. """

        newuser = { 'type': 'users',
                    'handle': 'testuser@foo.com',
                    'name': 'Test User',
                    'username':'ignored'} #Should be ignored!

        self.app.put('/users/testuser', newuser, status=200)

        newuser2 = self.app.get('/users/testuser', status=200).json

        newuser['username'] = 'testuser'
        del(newuser['type'])
        del(newuser2['id'])

        self.assertEqual(newuser2, newuser)

        self.app.get('/users/ignored', status=404)

    def test_get_my_details(self):
        """As an admin, fetching /users/<me> should produce exactly the
           same result as fetching /user
        """

        r1 = self.app.get('/users/administrator')
        r2 = self.app.get('/user')

        self.assertEqual(r1.json, r2.json)

    #!! Not implemented.
    @unittest.skip
    def test_update_user(self):
        """ Updating a user. Retrieve details. The results should reflect the
            change.
        """
        self.create_user('testuser')

        self.app.patch(           '/users/testuser',
                                  {'type': 'users',
                                  'handle': 'testuser@foo.com',
                                  'name': 'Test User Updated',
                                  'username':'testuser'})
        response = self.app.get('/users/testuser?actor_id=testuser')

        self.assertEqual(response.json['name'], 'Test User Updated')

    #!! Not implemented.
    @unittest.skip
    def test_update_self(self):
        """ Updating myself. Retrieve details. The results should reflect the
            change.
        """

        me = self.app.get('/user').json['username']

        response = self.app.patch('/users/' + me,
                                  {'type': 'users',
                                  'handle': 'testuser',
                                  'name': 'Test User Updated',
                                  'username':'testuser'},
                                  status=501)

        response = self.app.get('/users/' + me)

        self.assertEqual(response.json['name'], 'Test User Updated')

    #!! Not implemented.
    @unittest.skip
    def test_delete_user(self):
        """ Delete a user. Attempt to retrieve details should return 404.

        !! Not implemented - see notes about why this is tricky."""
        self.create_user('testuser')
        response = self.app.delete('/users/testuser')

        response = self.app.get('/users/testuser', status=404)

    def test_change_my_password(self):
        """ Apply a password to ourself. Check that we receive a 200 OK.
            Check that i can now log in with the new password.
            Note there is an equivalent test for a regular user setting their
            own password.
        """
        self.create_user('testuser')
        response = self.app.put('/users/administrator/password',
                                {'password': 'newpass'})

        #Force the server to forget the old password
        self.app.authorization = ('Basic', ('xxx', 'xxx'))
        self.app.get('/users/testuser', status=401)

        #The old password must now fail.
        self.app.authorization = ('Basic', ('administrator', 'adminpass'))
        self.app.get('/users/testuser', status=401)

        #The new one should now work
        self.app.authorization = ('Basic', ('administrator', 'newpass'))
        self.app.get('/users/testuser')



    def test_set_user_password(self):  # FIX
        """ Apply a password to a user. Check that we receive a 200 OK.
            Validate against the database with the user and password above.
        """

        self.create_user('testpassuser')

        self.app.put(           '/users/testpassuser/password',
                                {'password': 'testpass'})

        #Test login with new pass
        self.app.authorization = ('Basic', ('testpassuser', 'testpass'))
        response = self.app.get('/users/testpassuser', status=200)

    @unittest.skip
    def test_retrieve_user_touches(self):
        """ Retrieve a list of touches that the user has made to the database.
        This can only be requested by the user themselves, an agent or an
        administrator.

        !! Not implemented."""
        pass

    def test_invalid_user_credit(self):
        """ Query the credit for a non-existent user."""

        response = self.app.post('/users/notauser/credit',
                                {'credit': 1000},
                                status=404)
        response = self.app.get('/users/notauser/credit',
                                status=404)

    def test_create_retrieve_user_credit(self):
        """ Add credit to a user's account. This can only be done by an
        administrator."""

        self.create_user("testuser")

        self.app.post('/users/testuser/credit', {'credit': 1000})

        response = self.app.get('/users/testuser/credit', status=200)
        self.assertEqual(response.json['credit_balance'], 1000)
        uid = response.json['actor_id']

        # Debit 100, we should have 900 left
        response2 = self.app.post('/users/testuser/credit', {'credit': "-100"})

        self.assertEqual(response2.json, { 'actor_id' : uid,
                                           'credit_change' : -100,
                                           'credit_balance' : 900 } )

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

        self.app.post('/setup_states')

        # Create server
        self.create_server("testserver")

        def push_to_state(state):
            response = self.app.post('/servers/testserver/' + state)

        def get_state():
            response = self.app.get('/servers/testserver/state',
                            {'artifact_id': 'testserver'})
            return response.json


        #This should fail because not all the states are valid.
        for state in STATES_TO_TEST:
            res = push_to_state(state)
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

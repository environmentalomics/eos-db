"""Tests for DB API behaviour when logged in as user.

   Need to sort out which tests live here and which in test_vm_actions_http
"""
import os, sys
import unittest
from eos_db import server
from webtest import TestApp
from pyramid.paster import get_app
from http.cookiejar import DefaultCookiePolicy

# Depend on test.ini in the same dir as thsi file.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestUserAPI(unittest.TestCase):
    """Tests API functions associated with actions a regular user can take.
       Note that all tests are in-process, we don't actually start a HTTP server.
       All administrative requirements will be set up with direct calls
       to eos_db.server, and all user calls will be done via self.app.
    """
    def setUp(self):
        """Launch app using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)

        #We need to do this each time because restarting the app leads
        #to reloading test.conf.json defaults.
        self._override_boost_levels()

        #All auth via BasicAuth - never return the session cookie.
        self.app.cookiejar.set_policy(DefaultCookiePolicy(allowed_domains=[]))

        # This sets global var "engine" - in the case of SQLite this is a fresh RAM
        # DB each time.  If we only did this on class instantiation the database would
        # be dirty and one test could influence another.
        # TODO - add a test that tests this.
        server.choose_engine("SQLite")

        # Punch in new user account with direct server call
        # This will implicitly generate the tables.
        user_id = self.create_user("testuser")
        #Here is what the user should look like when inspected
        self.user_json =  { "name"    : "testuser testuser",
                            "handle"  : "testuser@example.com",
                            "id"      : 1,
                            "credits" : 0,
                            "username": "testuser"}

        #print("user_id is %s" % str(user_id))
        #print("user_from_db_is %s" % server.get_user_id_from_name("testuser"))

        server.touch_to_add_password(user_id, "asdf")

        # And log in as this user for all tests (via BasicAuth)
        # FIXME - switch to token auth to speed up the tests.
        self.app.authorization = ('Basic', ('testuser', 'asdf'))

    """Unauthenticated API functions.

       Should respond the same regardless of authentication.
    """

    def test_home_view(self):
        """ Home view should respond with 200 OK. """
        response = self.app.get('/', status=200)

    # Not sure why Ben implemented options, but it should still work.
    def test_options(self):
        """ Options should respond with 200 OK. """
        response = self.app.options('/', status=200)

    """User API functions.

    The user functions in the API are primarily used by system utilities.
    Creating a user and password, and validating against the database in
    order to receive an access token, are prerequisites for using functions
    in later sections of the API. These can only be called by an
    administrator."""

    def test_whoami(self):
        """ How do I find out who I am? """
        response = self.app.get('/user')

        #We expect to be user 1, as the database is fresh.
        #All other items should be as per create_user("testuser")
        self.assertEqual( response.json, self.user_json )

    def test_retrieve_my_info(self):
        """ Retrieving my own user info by name should give the same result
            as above."""

        response = self.app.get('/users/testuser', status=200)

        #We expect to be user 1, as the database is fresh.
        #All other items should be as per create_user("testuser")
        self.assertEqual( response.json, self.user_json )

    def test_retrieve_other_user_info(self):
        """ Retrieving info for another user should respond 200 OK. """

        self.create_user("anotheruser")

        self.assertEqual(self.app.get('/users/anotheruser').json['name'], "anotheruser anotheruser")

    def test_retrieve_users(self):
        """ Add another couple of users. Three records should be returned, as
            there is already a testuser. """

        self.create_user("foo")
        self.create_user("bar")

        response = self.app.get('/users')

        self.assertEqual(len(response.json), 3)

    #Unimplemented just now.
    @unittest.expectedFailure
    def test_delete_user(self):
        """ Delete a user. Should fail because the account does not have permission,
            but it actually fails because deletion is unimplemented.
        """
        self.create_user("anotheruser")
        response = self.app.delete('/users/anotheruser', status=404)


    def test_change_my_password(self):
        """ Apply a password to our user. Check that we receive a 200 OK.
            Check we can log in with the new password but not the old.
        """
        response = self.app.put('/user/password',
                                {'password': 'newpass'})

        #This should work
        self.app.authorization = ('Basic', ('testuser', 'newpass'))
        self.app.get('/users/testuser')


        #This should fail as the password is now wrong.
        self.app.authorization = ('Basic', ('testuser', 'asdf'))
        self.app.get('/users/testuser', status=401)

    def test_change_other_password(self):
        """ Try to change password for another user, which should fail.
        """
        self.create_user("anotheruser")

        response = self.app.put('/users/anotheruser/password',
                                {'password': 'newpass'},
                                status=401)

    def test_retrieve_user_credit(self):
        """ If administrator adds credit, I should be able to see it.
            See full credit tests in test_credit.py
        """
        self.add_credit(123, 'testuser')

        #And retrieve it back
        response = self.app.get('/user')

        user_json = self.user_json.copy()
        user_json['credits'] = 123

        self.assertEqual( response.json, user_json )


    def test_retrieve_servers(self):
        """ A user can request a list of servers that they own.
        """
        server_id = self.create_server('fooserver', 'testuser')

        my_servers = self.app.get('/servers').json

        self.assertTrue(server_id)

        self.assertEqual(len(my_servers), 1)
        self.assertEqual(my_servers[0]['artifact_name'], 'fooserver')

    def test_retrieve_user_touches(self):
        """ Retrieve a list of touches that the user has made to the database.
        This can only be requested by the user themselves, an agent or an
        administrator. """

    def test_create_server(self):
        """ A regular user cannot create a server or give themselves ownership
            of a server, so this should produce an appropriate error.
        """

    def test_create_server_owner(self):
        """ Add an owner to a server. Ensure that a 200 OK response results.
        """
        #FIXME - move this to administrator tests.

    """ Server State-Change Functions. """

    def test_start_server(self):
        """ Check that a server appears in state 'Starting' after using the
        relevant API call. This also tests the function 'retrieve_servers_in_state'.
        """
        server_id = self.create_server('fooserver', 'testuser')
        self.app.post('/servers/fooserver/Starting')

        #1 - server should appear to be Starting in list of my servers.
        my_servers = self.app.get('/servers').json
        self.assertEqual(len(my_servers), 1)
        self.assertEqual(my_servers[0]['state'], 'Starting')

        #2 - server should appear to be Starting if I look at it directly
        my_server = self.app.get('/servers/fooserver').json
        self.assertEqual(my_server['state'], 'Starting')

        #3 - server should appear as the only server in state Starting
        servers_in_state = self.app.get('/states/Starting').json
        self.assertEqual(len(servers_in_state), 1)
        self.assertEqual(servers_in_state[0]['artifact_name'], 'fooserver')

    def test_error_by_id_server(self):
        """ Check that i can put a server into Error state, refereced by ID
        """
        server_id = self.create_server('fooserver', 'testuser')
        self.app.post('/servers/by_id/%i/Error' % server_id)

        server_info = self.app.get('/servers/fooserver').json
        self.assertEqual(server_info['state'], 'Error')


    def _override_boost_levels(self):
        #Load our Boost levels
        conf = dict(BoostLevels={})

        conf['BoostLevels']['baseline'] = {
                'label' : 'test0',
                'ram'   :  16 ,
                'cores' :  1 }

        conf['BoostLevels']['levels'] = (
                { 'label'  : 'test1',
                  'ram'    :  40 ,
                  'cores'  :  2 ,
                  'cost'   :  1           },
                { 'label'  : 'test2',
                  'ram'    :  140 ,
                  'cores'  :  8 ,
                  'cost'   :  3           },
                { 'label'  : 'test3',
                  'ram'    :  400 ,
                  'cores'  :  16 ,
                  'cost'   :  12          },
            );

        conf['BoostLevels']['capacity'] = (
                ( 20,  0,  0 ),
                ( 15,  1,  0 ),
                ( 10,  2,  0 ),
                (  5,  3,  0 ),
                (  0,  4,  0 ),
                (  5,  0,  1 ),
                (  0,  1,  1 )
            );

        #Load up the new values
        server.set_config(conf)


    def test_boost_deboost_server(self):
        """ Test the boost call, which is done by putting the server into /Preparing.
            After this the server should be in the Preparing state and the user should
            have fewer credits.
            Also test the deboost.
        """

        server_id = self.create_server('boostme', 'testuser')
        self.add_credit(123, 'testuser')

        self.app.post('/servers/boostme/Preparing', params=dict(hours=20, cores=2, ram=40))

        #Check the user
        user_info = self.app.get('/user').json
        self.assertEqual(user_info['credits'], 103)

        #Check the server
        info_expected = dict(boosted="Boosted", boostremaining="19 hrs, 59 min", ram="40", cores="2")
        server_info = self.app.get('/servers/boostme').json
        #Remove items I don't want to compare from server_info
        info_got = {k:str(server_info[k]) for k in server_info if k in info_expected}

        self.assertEqual(info_got, info_expected)

        #Deboost and check again
        self.app.post('/servers/boostme/Pre_Deboosting')

        #Check the user - we should be down 1 credit.
        user_info = self.app.get('/user').json
        self.assertEqual(user_info['credits'], 122)

        #Check the server once more.
        info_expected = dict(boosted="Unboosted", boostremaining="N/A", ram="16", cores="1")
        server_info = self.app.get('/servers/boostme').json
        #Remove items I don't want to compare from server_info
        info_got = {k:str(server_info[k]) for k in server_info if k in info_expected}

        self.assertEqual(info_got, info_expected)

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

###############################################################################
# Support Functions, calling the server code directly                         #
###############################################################################

    def create_user(self, name):
        #Since we are not logged in as the administrator, do this directly
        return server.create_user("users", name + "@example.com", name + " " + name, name)

    # Servers should not normally have uuid set to name, but maybe for testing it doesn't
    # matter?
    def create_server(self, name, owner):
        owner_id = server.get_user_id_from_name(owner)
        server_id = server.create_appliance(name, name)

        server.touch_to_add_ownership(server_id, owner_id)

        return server_id

    def add_credit(self, amount, owner):
        owner_id = server.get_user_id_from_name(owner)

        server.touch_to_add_credit(owner_id, int(amount))

if __name__ == '__main__':
    unittest.main()

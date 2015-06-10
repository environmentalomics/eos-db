"""Tests the HybridAuth mechanism for authentication.
   See auth.py for an explanation of how this works.
"""
import os
import re
from io import StringIO
import unittest, requests
from eos_db import server
from webtest import TestApp
from http.cookiejar import DefaultCookiePolicy
from unittest.mock import patch
from pyramid.paster import get_app, get_appsettings

# Depend on test.ini and a secret in the same dir as thsi file.
test_ini    = os.path.join(os.path.dirname(__file__), 'test.ini')
secret_file = os.path.join(os.path.dirname(__file__), 'secret_file.txt')

class TestAgentAPI(unittest.TestCase):
    """Tests clients logging in as agents.
    """
    def setUp(self):
        """Launch pserve using webtest with test settings"""

        #Nope, do this for each test...
        #self.appconf = get_app(test_ini)
        #self.app = TestApp(self.appconf)

        server.choose_engine("SQLite")  # Sets global var "engine" - in the
                                        # case of SQLite this is a fresh RAM
                                        # DB each time.

        # Create new user. For not much reason.
        user_id = server.create_user("users", "testuser", "testuser", "testuser")
        server.touch_to_add_credit(user_id, 200)

    #Static method
    def _ini_filter(line):
        """Annoyingly, get_app() does not allow you a hook to modify the .ini
           data before the app is instantiated.
           A lesser man might make a modified version of the file,
           but I can use some cunning function patching to install this filter,
           and re-write the .ini file on the fly.
        """
        return re.sub(
                r'^agent.secret =.*',
                r'agent.secretfile = %s' % secret_file,
                line)

    #Static method
    def _ini_filter_del(line):
        """This version removes the line completely
        """
        return re.sub(
                r'^agent.secret =.*',
                r'',
                line)

    def test_the_test_1(self):
        """ Confirm that secret_file really does contain the text
            'testsharedsecret'
        """
        with open(secret_file) as ssfile:
            res = ssfile.read().rstrip('\n')

        self.assertEqual(res, 'testsharedsecret')

    def test_the_test_2(self):
        """ Confirm that the .ini file has the expected shared secret in it.
            Confirm that I can patch the .ini file to provide an app that uses
            the secret from secret_file
        """
        settings1 = get_appsettings(test_ini)
        self.assertEqual(settings1['agent.secret'], 'sharedsecret')

        with patch('builtins.open',
                   filter_open(TestAgentAPI._ini_filter, pattern=r'test\.ini$', verbose=False)):
            settings2 = get_appsettings(test_ini)

        self.assertEqual(settings2.get('agent.secret', 'None'), 'None')
        self.assertEqual(settings2.get('agent.secretfile', 'None'), secret_file)

    def test_bad_secret(self):
        """ The DB API should return a 401 unauthorised if I submit a request
            as an agent but with a bad or empty password.
        """
        app = TestApp(get_app(test_ini))

        #With no password
        app.authorization = ('Basic', ('agent', ''))
        app.get("/users/testuser/credit", status=401)

        #And with a bad one
        app.authorization = ('Basic', ('agent', 'badpass'))
        app.get("/users/testuser/credit", status=401)

    def _get_test_app(self):
        # This is tested in the test below, and also convenient for other tests where
        # we just want a working agent log-in.

        app = TestApp(get_app(test_ini))
        #Re-read the .ini to find out the secret.
        settings = get_appsettings(test_ini)

        #This should not be the same as what's in secret-file.txt.
        #Actually, I already tested this above, no matter.
        # self.assertNotEqual(settings['agent.secret'], 'testsharedsecret')
        app.authorization = ('Basic', ('agent', settings['agent.secret']))

        #And we need this, or else the second call will fail with
        # KeyError: 'No such user'.  Really we should either suppress HAP returning
        # a login token to agents or else allow it to validate the token successfully.
        app.cookiejar.set_policy(DefaultCookiePolicy(allowed_domains=[]))

        return app

    def test_secret_in_config(self):
        """ I should be able to set a secret in the config file and use
            it to log in.
        """
        app = self._get_test_app()

        r = app.get("/users/testuser/credit")
        self.assertEqual(r.json['credit_balance'], 200)

        #Also, there should be no auth cookie returned, since it can't be used to log in.
        self.assertIsNone(r.headers.get('Set-Cookie'))

    def test_secret_in_file(self):
        """ Likewise I should be able to set a secretfile in the config file
            and the secret should be read from there.
        """
        #self test 2 above confirms that this sets the agent.secretfile correctly
        with patch('builtins.open',
                   filter_open(TestAgentAPI._ini_filter, pattern=r'test\.ini$', verbose=False)):
            appconf = get_app(test_ini)

        app = TestApp(appconf)

        # We know what's in the secret_file; see the first test above
        app.authorization = ('Basic', ('agent', 'testsharedsecret'))

        r = app.get("/users/testuser/credit")
        self.assertEqual(r.json['credit_balance'], 200)

    def test_missing_secret(self):
        """ If I try to start an instance of the app without a suitable agent secret
            I should get a nasty error
        """
        with patch('builtins.open',
                   filter_open(TestAgentAPI._ini_filter_del, pattern=r'\.ini$', verbose=False)):
            self.assertRaises(ValueError, get_app, test_ini)

    def test_env_secretfile(self):
        """ I should be able to supply the secret in the environment and it should
            override the config file.
        """
        #Don't do this, it stays set and breaks other tests
        #os.environ['agent_secretfile'] = secret_file
        #Do this...
        with patch.dict('os.environ', {'agent_secretfile': secret_file}):
           app = TestApp(get_app(test_ini))

        # We know what's in the secret_file; see the first test above
        app.authorization = ('Basic', ('agent', 'testsharedsecret'))

        r = app.get("/users/testuser/credit")
        self.assertEqual(r.json['credit_balance'], 200)

    def test_env_badfile(self):
        """ If I try to reference a bad secretfile in the environment it should complain,
            even if a valid secretfile is specified in the config file.
        """
        with patch('builtins.open',
                   filter_open(TestAgentAPI._ini_filter, pattern=r'\.ini$', verbose=False)):
            with patch.dict('os.environ', {'agent_secretfile': "NOT_A_REAL_FILE_12345"}):
                self.assertRaises(FileNotFoundError, get_app, test_ini)

    def test_env_token_badfile(self):
        """ If I try to reference a bad secretfile in the environment it should complain,
            even if a valid secretfile is specified in the config file.
            This should apply to the token secret too.
        """
        with patch.dict('os.environ', {'authtkt_secretfile': "NOT_A_REAL_FILE_12345"}):
            self.assertRaises(FileNotFoundError, get_app, test_ini)

    # Note that detailed tests for get(/states) and get(/states/XYZ) are in test_vm_actions_http
    def test_states_empty(self):
        #Get a valid log-in
        app = TestApp(get_app(test_ini))
        settings = get_appsettings(test_ini)
        app.authorization = ('Basic', ('agent', settings['agent.secret']))

        r = app.get('/states')

        self.assertEqual(r.json, { s : 0 for s in server.get_state_list() })

    # Test for the deboost daemon.
    def test_get_deboost_jobs(self):
        #Create 4 servers and boost them all to 40GB + 2cores.
        #Set deboost times at 14hrs ago, 1 hr ago, 0, and 1 hour hence
        #Call /deboost_jobs?past=24;future=12 should see all 4
        #Call /deboost_jobs?past=12 should see 2
        #Deboost VM2, then /get_deboost_jobs?past=12 should see 1

        #/get_deboost_jobs returns [ dict(boost_remain=123, artifact_id=..., artifact_name=...)]
        app = self._get_test_app()

        servers = ['srv1', 'srv2', 'srv3', 'srv4']
        times   = [  -14 ,    -1 ,     0 ,     1 ]
        user_id = create_user('someuser')
        for s, hours in zip(servers, times):
            vm_id = create_server(s, user_id)
            server.touch_to_add_specification(vm_id, 2, 40)
            server.touch_to_add_deboost(vm_id, hours)

        #Negative time deboost should be OK
        #Confirm the negative-time deboost worked (eternal + internal view)
        server_1_info = app.get('/servers/srv1').json
        self.assertEqual(server_1_info['boostremaining'], "N/A")

        server_1_tud = server.get_time_until_deboost(server_1_info['artifact_id'])
        self.assertTrue(server_1_tud[1] < (-13 * 60 * 60))

        #Look for all jobs - should be 4
        dj1 = app.get('/deboost_jobs', dict(past=24, future=12)).json
        self.assertEqual(len(dj1), 4)

        #Look for jobs in last 12 hours (what the deboost_daemon will normally do)
        dj2 = app.get('/deboost_jobs', dict(past=12)).json
        self.assertEqual( set(s['artifact_name'] for s in dj2), set(('srv2', 'srv3')) )

        #And if we deboost VM2 (via an API call, why not!)...
        app.post('/servers/srv2/specification', dict(cores=1, ram=16))
        dj3 = app.get('/deboost_jobs', dict(past=12)).json
        self.assertEqual( set(s['artifact_name'] for s in dj3), set(('srv3',)) )


###############################################################################
# Helper code, lets me modify file contents on-the-fly.                       #
###############################################################################

class filter_open:
    """ A hook on open() that allows me to modify file contents on-the-fly.
        Use it to patch a function like so:
            @patch('builtins.open', filter_open(my_filt, pattern=".txt$"))
        Note this only supports a single global filter rule, applied
        according to a single filename pattern match.
    """
    def __init__(self, filter, pattern=r'.*', verbose=True):
        self.filter = filter
        self.v = verbose
        self.p = pattern

    def __call__(self, *args, open=open, **kwargs):
        v = self.v
        if v: print("Opening " + args[0])
        fh = open(*args, **kwargs)
        if not re.search(self.p, fh.name):
            if v: print("Not applying filter - filename !~ /%s/" % self.p)
            return fh
        elif fh.mode != 'r':
            if v: print("Not applying filter - mode != 'r'")
            return fh
        else:
            if v: print("Applying filter")
            filtered = ''.join( self.filter(line) for line in fh )
            fh.close()
            return StringIO(filtered)

###############################################################################
# Support Functions, calling the server code directly (from test_user_api)    #
###############################################################################

def create_user(name):
    #Since we are not logged in as the administrator, do this directly
    return server.create_user("users", name + "@example.com", name + " " + name, name)

# Servers should not normally have uuid set to name, but maybe for testing it doesn't
# matter?
def create_server(name, owner_id):
    server_id = server.create_appliance(name, name)
    server.touch_to_add_ownership(server_id, owner_id)

    return server_id

def add_credit(amount, owner):
    owner_id = server.get_user_id_from_name(owner)
    server.touch_to_add_credit(owner_id, int(amount))

if __name__ == '__main__':
    unittest.main()

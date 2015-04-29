"""Tests the HybridAuth mechanism for authentication.
   See auth.py for an explanation of how this works.
"""
import os
import re
from io import StringIO
import unittest, requests
from eos_db import server
from webtest import TestApp
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

        # Create new user. This will implicitly generate the tables.
        user_id = server.create_user("users", "testuser", "testuser", "testuser")
        server.touch_to_add_credit(user_id, 200)

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
                   filter_open(TestAgentAPI._ini_filter, pattern=r'\.ini$', verbose=False)):
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

    def test_secret_in_config(self):
        """ I should be able to set a secret in the config file and use
            it to log in.
        """
        app = TestApp(get_app(test_ini))
        #Re-read the .ini to find out the secret.
        settings = get_appsettings(test_ini)

        app.authorization = ('Basic', ('agent', settings['agent.secret']))

        r = app.get("/users/testuser/credit")
        self.assertEqual(r.json['credit_balance'], 200)

        #Note, I should also get an auth cookie, but don't actually care.

    def test_secret_in_file(self):
        """ Likewise I should be able to set a secretfile in the config file
            and the secret should be read from there.
        """
        #self test 2 above confirms that this sets the agent.secretfile correctly
        with patch('builtins.open',
                   filter_open(TestAgentAPI._ini_filter, pattern=r'\.ini$', verbose=False)):
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
            self.assertRaises(TypeError, get_app, test_ini)

####### Helper code, lets me modify file contents on-the-fly.

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
########

if __name__ == '__main__':
    unittest.main()

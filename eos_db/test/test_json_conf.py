"""Tests that the config file is read on startup.
"""
import os, sys
import unittest
from eos_db import server
from webtest import TestApp
from pyramid.paster import get_app
from http.cookiejar import DefaultCookiePolicy

# Depend on test.ini in the same dir as thsi file.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestJSONConf(unittest.TestCase):
    """Tests that the configuration file is loaded.
    """
    def setUp(self):
        """Launch app using webtest with test settings"""
        self.appconf = get_app(test_ini)
        self.app = TestApp(self.appconf)

    def test_conf_loaded(self):
        """There is a test.json.conf in the test directory, so just check
           that things from there got picked up by peering directly into
           the server object.
        """

        #test_the_test
        self.assertTrue(os.path.isfile(
            os.path.join(os.path.dirname(__file__), 'test.settings.json')
        ))

        bl = server.get_boost_levels()
        self.assertEqual(bl['baseline']['label'], 'test_baseline')

        sl = server.get_state_list()
        self.assertEqual(sl[-1], 'TestExtraState')

    def test_new_conf(self):
        """This time, load an alternative file
        """
        newconf = os.path.join(os.path.dirname(__file__), 'test2.settings.json')

        #test_the_test
        self.assertTrue(os.path.isfile(newconf))

        server.load_config_json(newconf)

        bl = server.get_boost_levels()
        self.assertEqual(bl['baseline']['label'], 'test2_baseline')

        self.assertEqual(bl['levels'][0]['label'], 'test2_boost1')

        sl = server.get_state_list()
        self.assertEqual(sl[-1], 'Test2ExtraState')

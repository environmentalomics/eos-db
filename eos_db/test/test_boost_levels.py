import unittest
import sys, os, imp
from webtest import TestApp
from pyramid.paster import get_app

from eos_db import server

# Normally I'd frown upon any code that discovers it's own location, but in this
# case it makes sense to use test.ini from the same folder as the test module.
test_ini = os.path.join(os.path.dirname(__file__), 'test.ini')

class TestBoostLevels(unittest.TestCase):
    """Tests to see that the server deals correctly with reconfiguring Boost
       levels.
    """
    def setUp(self):
        """Launch pserve/waitress using webtest with test settings.
           Fresh for every test, though it shouldn't matter.
        """
        self.myapp = get_app(test_ini)
        self.testapp = TestApp(self.myapp)

        #No auth
        self.testapp.authorization = None

    def test_get_def_boost_levels(self):

        # Note that vlaues will now be loaded automatically from test.conf.ini

        r = self.testapp.get('/boostlevels')

        self.assertEqual(r.json['baseline']['cores'], 1)
        self.assertEqual(r.json['levels'], [])
        self.assertEqual(r.json['capacity'], [])

    def test_good_boost_levels(self):

        # With the original code we had to embed the settings into a settings.py file.
        # Now we have the settings in a .json file with the same name as the .ini file
        # - ie. production.conf.json, development.conf.json, test.conf.json.
        # But we can also load new settings.

        conf = dict(BoostLevels={})

        conf['BoostLevels']['baseline'] = {
                'label' : 'test0',
                'ram'   :  3 ,
                'cores' :  1 ,
                'cost'  :  0  }

        conf['BoostLevels']['levels'] = (
                { 'label'  : 'test1',
                  'ram'    :  10 ,
                  'cores'  :  2 ,
                  'cost'   :  1           },
                { 'label'  : 'test2',
                  'ram'    :  20 ,
                  'cores'  :  8 ,
                  'cost'   :  3           },
                { 'label'  : 'test3',
                  'ram'    :  30 ,
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

        r = self.testapp.get('/boostlevels')

        self.assertEqual(r.json['baseline']['ram'],  3)
        self.assertEqual(len(r.json['levels']),      3)
        self.assertEqual(len(r.json['capacity'][2]), 3)



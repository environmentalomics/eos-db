"""
Test for Error on non-integer credits
Test for Error on non-actor
Test to check correct addition of credits
Test to check correct subtraction of credits
Test to ensure correct credits returned by API get
"""

import unittest
import subprocess
import threading
import signal
import os
import requests
from eos_db.server import override_engine, create_user, touch_to_add_credit
from eos_db.server import check_credit, check_actor_id

class TestCreditFunctions(unittest.TestCase):
    """Tests credit functions in server module."""
    
    def test_create_user(self):
        """
        Add a user.
        """
        override_engine('sqlite://')
        user = create_user('user','testuser','testuser','testuser')
        exists = check_actor_id(user)
        assert exists
    
    def test_add(self):
        """
        Behaviour: Calling the API to add credit should result credit being added to
        the database.
        """
        override_engine('sqlite://')
        user = create_user('user','testuser2','testuser2','testuser2')
        touch_to_add_credit(user,1000)
        credit = check_credit(user)
        assert credit == 1000
        
    
    def test_subtract(self):
        """
        Behaviour: Calling the API to add credit should result credit being
        subtracted from the database.
        """
        override_engine('sqlite://')
        user = create_user('user', 'testuser3', 'testuser3', 'testuser3')
        touch_to_add_credit(user,-500)
        credit = check_credit(user)
        assert credit == -500

class TestCreditAPI(unittest.TestCase):
    """Tests credit API as separate process"""
    
    def setUp(self):
        self.pserve = PServeThread()
        self.pserve.start()
    
    def test_create_user(self):
        assert 1 == 1

    def test_add_credit(self):
        assert 1 == 1
    
    def test_subtract_credit(self):
        assert 1 == 1
        
    def tearDown(self): 
        #self.pserve.destroy()
        pass

class PServeThread(threading.Thread):
    """ """
    
    def __init__(self):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

    def run(self):
        """ Open pserve as a subprocess with a database server override. """
        self.p = subprocess.Popen('pserve ../../development.ini'.split(),
                             shell=False,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.stdout, self.stderr = self.p.communicate()

    def destroy(self):
        self.p.kill()
        
if __name__ == '__main__':
    unittest.main()
    
#class TestAPI(unittest.TestCase):
#    def test_400(self):
#        
#        
#    def test_403(self):
        
#class TestWebFunctionality(unittest.TestCase):
    
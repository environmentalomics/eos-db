"""Tests for credit addition, subtraction and querying.
"""

import unittest
import requests
from eos_db.server import override_engine, create_user, touch_to_add_credit
from eos_db.server import check_credit, check_actor_id
from eos_db.test.dummy_server import PServeThread

class TestCreditFunctions(unittest.TestCase):
    """Tests credit functions in server module."""
    
    def setUp(self):
        override_engine('sqlite://')
    
    def test_create_user(self):
        """
        Add a user.
        """
        user = create_user('user','testuser','testuser','testuser')
        exists = check_actor_id(user)
        assert exists
    
    def test_add(self):
        """
        Behaviour: Calling the API to add credit should result credit being added to
        the database.
        """
        user = create_user('user','testuser2','testuser2','testuser2')
        touch_to_add_credit(user,1000)
        credit = check_credit(user)
        assert credit == 1000
        
    
    def test_subtract(self):
        """
        Behaviour: Calling the API to add credit should result credit being
        subtracted from the database.
        """
        user = create_user('user', 'testuser3', 'testuser3', 'testuser3')
        touch_to_add_credit(user,-500)
        credit = check_credit(user)
        assert credit == -500

class TestCreditAPI(unittest.TestCase):
    """Tests credit API as separate process"""
    
    pserve = PServeThread()
    pserve.start()    
    
    def test_create_user(self):
        assert 1 == 1

    def test_add_credit(self):
        assert 1 == 1
    
    def test_subtract_credit(self):
        assert 1 == 1
        
    def tearDown(self): 
        TestCreditAPI.pserve.destroy()
        
if __name__ == '__main__':
    unittest.main()
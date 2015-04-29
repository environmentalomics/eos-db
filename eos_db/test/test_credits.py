"""Tests for credit addition, subtraction and querying.
   See also tests in test_user_api
"""

import unittest
import requests

from eos_db.server import choose_engine, create_user, touch_to_add_credit
from eos_db.server import check_credit, check_actor_id

class TestCreditFunctions(unittest.TestCase):
    """Tests credit functions in server module."""

    def setUp(self):
        choose_engine('SQLite')

    def test_create_user(self):
        """
        Add a user.
        """
        user = create_user('user','testuser','testuser','testuser')
        self.assertEqual(check_actor_id(user), user)

    def test_add(self):
        """
        Behaviour: Calling the API to add credit should result credit being added to
        the database.
        """
        user = create_user('user','testuser2','testuser2','testuser2')
        touch_to_add_credit(user,1000)
        credit = check_credit(user)
        self.assertEqual(credit, 1000)

    def test_subtract(self):
        """
        Behaviour: Calling the API to add credit should result credit being
        subtracted from the database.
        """
        user = create_user('user', 'testuser3', 'testuser3', 'testuser3')
        touch_to_add_credit(user,-500)
        credit = check_credit(user)
        self.assertEqual(credit, -500)


if __name__ == '__main__':
    unittest.main()

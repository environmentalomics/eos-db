import unittest
from eos_db.models import Base, User, engine
from sqlalchemy.orm import sessionmaker

class TestUserActions(unittest.TestCase):
    """Tests actions which modify user account details"""
    
    def test_newuser(self):
        """Test creation of a new user.
        """
        Base.metadata.create_all(engine)
        new_user = User(name='Ben Collier', username='Ben Collier', type='user', uuid='asdasd', handle='hamsterman')
        Session = sessionmaker(bind=engine)
        session = Session()
        session.add(new_user)
        our_user = session.query(User).filter_by(name='Ben Collier').first()
        
    def tearDown(self):
        pass
    
if __name__ == '__main__':
    unittest.main()
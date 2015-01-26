import unittest
from eos_db.models import Base, User, engine
from sqlalchemy.orm import sessionmaker

class TestServerFunctions(unittest.TestCase):
    
    def test_newuser(self):
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
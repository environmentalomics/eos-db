"""Tests for VM actions.
This test suite avoids webtest and calls server functions directly.

"""

import unittest
from eos_db.server import (check_state,
                           setup_states,
                           get_state_list,
                           create_artifact_state,
                           deploy_tables,
                           choose_engine,
                           create_appliance,
                           touch_to_state,
                           touch_to_add_specification,
                           get_latest_specification,
                           get_previous_specification,
                           get_state_id_by_name,
                           get_server_id_from_name,
                           get_server_id_from_uuid,
                           return_artifact_details)

# FIXME - use the list from server.py
STATE_LIST = ["Starting",       # Machine was stopped, now starting up.
              "Stopping",       # Machine was started, now stopping.
              "Started",        # Machine is running.
              "Stopped",        # Machine is stopped.
              "Preparing",      # Stopping machine before a spec change.
              "Boosting",       # Changing specs.
              "Pre_Deboosting", # Preparing for deboost.
              "Restarting",     # Restarting machine.
              "Deboosting"]     # Changing specs.

# These tests are not good.  Skip them for now.
#@unittest.skip
class TestVMFunctions(unittest.TestCase):
    """Tests VM actions in server module.
    """
    def setUp(self):
        choose_engine('SQLite')
        deploy_tables()

#         for state in STATE_LIST:
#             create_artifact_state(state)
        #Surely:
        setup_states()

#         new_user = User(name='Test User', username='testuser', type='user', uuid='x', handle='testuser')
#         Session = sessionmaker(bind=engine)
#         session = Session()
#         session.add(new_user)
#         self.our_user = session.query(User).filter_by(uuid='x').first()

        # Not a real UUID!
        self._uuid = 48878

    # Create an appliance with a dummy UUID.
    def my_create_appliance(self, name):
        self._uuid += 1
        return create_appliance(name, self._uuid)

    # These 6 are probably redundant now we test all the calls via the web API?
    def test_start_server(self):
        """Check touch_to_state puts a server into "Started" state.
        """
        artifact_id = self.my_create_appliance("teststarted")
        touch_to_state(None, artifact_id, "Started")
        status = check_state(artifact_id)
        self.assertEqual(status, "Started")

    def test_stop_server(self):
        """Check touch_to_state puts a server into "Stopped" state.
        """
        artifact_id = self.my_create_appliance("teststopped")
        touch_to_state(None, artifact_id, "Stopped")
        status = check_state(artifact_id)
        self.assertEqual(status, "Stopped")

    def test_prestart_server(self):
        """Check touch_to_state puts a server into "Starting" state.
        """
        artifact_id = self.my_create_appliance("teststart")
        touch_to_state(None, artifact_id, "Starting")
        status = check_state(artifact_id)
        self.assertEqual(status, "Starting")

    def test_restart_server(self):
        """Check touch_to_state puts a server into "Restarting" state.
        """
        artifact_id = self.my_create_appliance("testrestart")
        touch_to_state(None, artifact_id, "Restarting")
        status = check_state(artifact_id)
        self.assertEqual(status, "Restarting")

    def test_preboost_server(self):
        """Check touch_to_state puts a server into "Preparing" state.
        """
        artifact_id = self.my_create_appliance("testpreboost")
        touch_to_state(None, artifact_id, "Preparing")
        status = check_state(artifact_id)
        self.assertEqual(status, "Preparing")

    @unittest.expectedFailure
    def test_boost_server(self):
        """Check touch_to_state puts a server into "Boosting" state.
            ** Expected fail - Boosting state was removed
        """
        artifact_id = self.my_create_appliance("testboost")
        touch_to_state(None, artifact_id, "Boosting")
        status = check_state(artifact_id)
        self.assertEqual(status, "Boosting")

    def test_server_invalid_state(self):
        """Check touch_to_state won't put a server into "BAD" state.
        """
        artifact_id = self.my_create_appliance("testbad")
        #But which exception?  Currently we get a TypeError
        with self.assertRaises(Exception):
            touch_to_state(None, artifact_id, "BAD")

    def test_add_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = self.my_create_appliance("testspecification")
        touch_to_add_specification(artifact_id,2,4)
        cores, ram = get_latest_specification(artifact_id)
        self.assertEqual(cores, 2)
        self.assertEqual(ram, 4)

    def test_read_previous_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = self.my_create_appliance("testspecification2")
        touch_to_add_specification(artifact_id,2,4)
        touch_to_add_specification(artifact_id,4,8)
        cores, ram = get_previous_specification(artifact_id,1)
        self.assertEqual(cores, 2)
        self.assertEqual(ram, 4)
        cores, ram = get_latest_specification(artifact_id)
        self.assertEqual(cores, 4)
        self.assertEqual(ram, 8)

    def test_get_state_by_name(self):
        """We expect the states created in setUp to be numbered sequentially
        """
        self.assertEqual(
            [ get_state_id_by_name(state) for state in get_state_list() ],
            [ n+1 for n in range(len(get_state_list()))]
        )

    def test_get_server_id_from_name(self):
        artifact_id = self.my_create_appliance("getname")
        returned_id = get_server_id_from_name("getname")
        self.assertEqual(artifact_id, returned_id)

    def test_get_server_id_from_uuid(self):
        artifact_id = self.my_create_appliance("getuuid")
        server_details = return_artifact_details(artifact_id)

        uuid = server_details['artifact_uuid']
        returned_id = get_server_id_from_uuid(uuid)
        self.assertEqual(artifact_id, returned_id)

    def test_return_artifact_details(self):
        """
        We expect a dictionary returned in JSON format, containing, amongst
        other things a uuid, state and server name.
        """
        artifact_id = self.my_create_appliance("returndetails")
        server_details = return_artifact_details(artifact_id)

        self.assertEqual(server_details['artifact_id'], artifact_id)
        self.assertEqual(server_details['state'], "Not yet initialised")
        self.assertEqual(server_details['artifact_name'], "returndetails")


if __name__ == '__main__':
    unittest.main()

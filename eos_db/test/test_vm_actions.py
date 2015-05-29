"""Tests for VM actions.
This test suite avoids webtest and calls server functions directly.

"""

import unittest
import eos_db.server as s

# These tests are not good.  Skip them for now.
#@unittest.skip
class TestVMActions(unittest.TestCase):
    """Tests VM actions in server module.
    """
    def setUp(self):
        s.override_engine('sqlite://', echo=False)

        #Need this since I called override_engine rather than choose_engine
        s.setup_states(ignore_dupes=False)

        # Not a real UUID!
        self._uuid = 48878

    # Create an appliance with a dummy UUID.
    def my_create_appliance(self, name):
        self._uuid += 1
        return s.create_appliance(name, str(self._uuid))

    # These 6 are probably redundant now we test all the calls via the web API?
    def test_start_server(self):
        """Check touch_to_state puts a server into "Started" state.
        """
        artifact_id = self.my_create_appliance("teststarted")
        s.touch_to_state(None, artifact_id, "Started")
        status = s.check_state(artifact_id)
        self.assertEqual(status, "Started")

    def test_stop_server(self):
        """Check touch_to_state puts a server into "Stopped" state.
        """
        artifact_id = self.my_create_appliance("teststopped")
        s.touch_to_state(None, artifact_id, "Stopped")
        status = s.check_state(artifact_id)
        self.assertEqual(status, "Stopped")

    def test_prestart_server(self):
        """Check touch_to_state puts a server into "Starting" state.
        """
        artifact_id = self.my_create_appliance("teststart")
        s.touch_to_state(None, artifact_id, "Starting")
        status = s.check_state(artifact_id)
        self.assertEqual(status, "Starting")

    def test_restart_server(self):
        """Check touch_to_state puts a server into "Restarting" state.
        """
        artifact_id = self.my_create_appliance("testrestart")
        s.touch_to_state(None, artifact_id, "Restarting")
        status = s.check_state(artifact_id)
        self.assertEqual(status, "Restarting")

    def test_preboost_server(self):
        """Check touch_to_state puts a server into "Preparing" state.
        """
        artifact_id = self.my_create_appliance("testpreboost")
        s.touch_to_state(None, artifact_id, "Preparing")
        status = s.check_state(artifact_id)
        self.assertEqual(status, "Preparing")

    def test_server_invalid_state(self):
        """Check touch_to_state won't put a server into "BAD" state.
        """
        artifact_id = self.my_create_appliance("testbad")
        #But which exception?  Currently we get a TypeError
        with self.assertRaises(Exception):
            s.touch_to_state(None, artifact_id, "BAD")

    def test_add_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = self.my_create_appliance("testspecification")
        s.touch_to_add_specification(artifact_id,2,4)
        cores, ram = s.get_latest_specification(artifact_id)
        self.assertEqual(cores, 2)
        self.assertEqual(ram, 4)

    def test_read_previous_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = self.my_create_appliance("testspecification2")
        s.touch_to_add_specification(artifact_id,2,4)
        s.touch_to_add_specification(artifact_id,4,8)
        cores, ram = s.get_previous_specification(artifact_id,1)
        self.assertEqual(cores, 2)
        self.assertEqual(ram, 4)
        cores, ram = s.get_latest_specification(artifact_id)
        self.assertEqual(cores, 4)
        self.assertEqual(ram, 8)

    def test_get_state_by_name(self):
        """We expect the states created in setUp to be numbered sequentially
        """
        self.assertEqual(
            [ s.get_state_id_by_name(state) for state in s.get_state_list() ],
            [ n+1 for n in range(len(s.get_state_list()))]
        )

    def test_get_server_id_from_name(self):
        artifact_id = self.my_create_appliance("getname")
        returned_id = s.get_server_id_from_name("getname")
        self.assertEqual(artifact_id, returned_id)

    def test_get_server_id_from_dupe(self):
        """I'm not sure what the original thinking was, but the schema
           allows me to create 2 servers with the same name, in which case
           I want the newest one back when I search.
        """
        artifact1 = self.my_create_appliance("dupe")
        self.assertEqual(s.get_server_id_from_name("dupe"), artifact1)

        #In an earlier bug an arbitrary server was returned.  Hard to
        #test reliably for this situation.
        artifact2 = self.my_create_appliance("dupe")
        self.assertNotEqual(artifact2, artifact1)
        self.assertEqual(s.get_server_id_from_name("dupe"), artifact2)

        artifact3 = self.my_create_appliance("dupe")
        self.assertEqual(s.get_server_id_from_name("dupe"), artifact3)

    def test_get_server_id_from_uuid(self):
        artifact_id = self.my_create_appliance("getuuid")
        server_details = s.return_artifact_details(artifact_id)

        uuid = server_details['artifact_uuid']
        returned_id = s.get_server_id_from_uuid(uuid)
        self.assertEqual(artifact_id, returned_id)

    def test_return_artifact_details(self):
        """
        We expect a dictionary returned in JSON format, containing, amongst
        other things a uuid, state and server name.
        """
        artifact_id = self.my_create_appliance("returndetails")
        server_details = s.return_artifact_details(artifact_id)

        self.assertEqual(server_details['artifact_id'], artifact_id)
        self.assertEqual(server_details['state'], "Not yet initialised")
        self.assertEqual(server_details['artifact_name'], "returndetails")

    def test_ownership(self):
        artifact_id = self.my_create_appliance("owned")
        artifact2_id = self.my_create_appliance("unowned")
        owner_id = s.create_user("users", "foo@example.com", "foo foo", "foo") 
        s.touch_to_add_ownership(artifact_id, owner_id)

        # Test that the user really owns the server.
        self.assertTrue(s.check_ownership(artifact_id, owner_id))

        # Test that the user does not own the second server.
        self.assertFalse(s.check_ownership(artifact2_id, owner_id))

if __name__ == '__main__':
    unittest.main()

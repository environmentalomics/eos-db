"""Tests for VM actions - start, stop, suspend.

"""

import unittest
from eos_db.server import (check_state,
                           setup_states,
                           deploy_tables,
                           override_engine,
                           create_appliance,
                           touch_to_prestart,
                           touch_to_prestop,
                           touch_to_prepare,
                           touch_to_boost,
                           touch_to_start,
                           touch_to_stop,
                           touch_to_add_specification,
                           get_latest_specification,
                           get_previous_specification,
                           get_state_id_by_name,
                           get_server_id_from_name,
                           return_artifact_details)

STATE_LIST = ["Starting",   # Machine was stopped, now starting up.
              "Stopping",   # Machine was started, now stopping.
              "Started",    # Machine is running.
              "Stopped",    # Machine is stopped.
              "Preparing",  # Stopping machine before a spec change.
              "Boosting"]   # Changing specs.

class TestVMFunctions(unittest.TestCase):
    """Tests VM actions in server module.
    """
    def setUp(self):
        override_engine('sqlite://')
        deploy_tables()
        setup_states(STATE_LIST)

    def test_start_server(self):
        """Check touch_to_start puts a server into "Started" state.
        """
        artifact_id = create_appliance("teststarted")
        touch_to_start(artifact_id)
        status = check_state(artifact_id)
        assert status == "Started"

    def test_stop_server(self):
        """Check touch_to_stop puts a server into "Stopped" state.
        """
        artifact_id = create_appliance("teststopped")
        touch_to_stop(artifact_id)
        status = check_state(artifact_id)
        assert status == "Stopped"

    def test_prestart_server(self):
        """Check touch_to_prestart puts a server into "Starting" state.
        """
        artifact_id = create_appliance("teststart")
        touch_to_prestart(artifact_id)
        status = check_state(artifact_id)
        assert status == "Starting"

    def test_prestop_server(self):
        """Check touch_to_prestop puts a server into "Stopping" state.
        """
        artifact_id = create_appliance("teststop")
        touch_to_prestop(artifact_id)
        status = check_state(artifact_id)
        assert status == "Stopping"

    def test_preboost_server(self):
        """Check touch_to_prestop puts a server into "Preparing" state.
        """
        artifact_id = create_appliance("testpreboost")
        touch_to_prepare(artifact_id)
        status = check_state(artifact_id)
        assert status == "Preparing"

    def test_boost_server(self):
        """Check touch_to_prestop puts a server into "Boosting" state.
        """
        artifact_id = create_appliance("testboost")
        touch_to_boost(artifact_id)
        status = check_state(artifact_id)
        assert status == "Boosting"

    def test_add_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = create_appliance("testspecification")
        touch_to_add_specification(artifact_id,2,4)
        cores, ram = get_latest_specification(artifact_id)
        assert cores == 2
        assert ram == 4

    def test_read_previous_specification(self):
        """Add a specification to a machine and recall it."""
        artifact_id = create_appliance("testspecification2")
        touch_to_add_specification(artifact_id,2,4)
        touch_to_add_specification(artifact_id,4,8)
        cores, ram = get_previous_specification(artifact_id,1)
        assert cores == 2
        assert ram == 4
        cores, ram = get_latest_specification(artifact_id)
        assert cores == 4
        assert ram == 8

    def test_get_state_by_name(self):
        i = 1
        for state in STATE_LIST:
            assert get_state_id_by_name(state) == i
            i += 1

    def test_get_server_id_from_name(self):
        artifact_id = create_appliance("getname")
        returned_id = get_server_id_from_name("getname")
        assert artifact_id == returned_id

    def test_return_artifact_details(self):
        """
        We expect a dictionary returned in JSON format, containing, amongst
        other things a uuid, state and server name.
        """
        artifact_id = create_appliance("returndetails")
        server_details = return_artifact_details(artifact_id)
        assert server_details['artifact_id'] == artifact_id
        assert server_details['state'] == "Not yet initialised"
        assert server_details['artifact_uuid'] == "returndetails"

if __name__ == '__main__':
    unittest.main()

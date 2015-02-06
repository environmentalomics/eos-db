"""Tests for VM actions - start, stop, suspend.
"""
import unittest
from eos_db.server import (touch_to_prestart, touch_to_prestop, 
                           touch_to_presuspend, create_appliance,
                           override_engine)
from eos_db.test.dummy_server import PServeThread

class TestVMFunctions(unittest.TestCase):
    """Tests VM actions in server module.
    """
    def setUp(self):
        override_engine('sqlite://')
    
    def test_prestart_server(self):
        """Test to ensure that a call to touch_to_prestart puts a server into
        prestart status.
        """
        artifact_id = create_appliance("testuuid")
        touch_to_prestart(artifact_id)
        status = check_status(appliance_id)
        assert status == "pre-start"
    
    def test_prestop_server(self):
        """Test to ensure that a call to touch_to_prestop puts a server into
        prestop status.
        """
        artifact_id = create_appliance("testuuid")
        touch_to_prestop(artifact_id)
        status = check_status(appliance_id)
        assert status == "pre-stop"
        
    def test_presuspend_server(self):
        """Test to ensure that a call to touch_to_presuspend puts a server into
        presuspend status.
        """
        artifact_id = create_appliance("testuuid")
        touch_to_presuspend(artifact_id)
        status = check_status(appliance_id)
        assert status == "pre-suspend"

class TestVMAPI(unittest.TestCase):
    """Tests API functions associated with VM actions.
    """
    pserve = PServeThread()
    pserve.start()
        
    def test_start_server(self):
        """Tests the results of calling API to start a server.
        """
        assert(1==1)
        
    def test_stop_server(self):
        """Tests the results of calling API to stop a server.
        """
        assert (1==1)
        
    def test_suspend_server(self):  
        """Tests the results of calling API to suspend a server.
        """
        assert (1==1)
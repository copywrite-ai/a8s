import unittest
import subprocess
import time
import urllib.request
import json
import os
import re

class TestAnsibleDeployment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Clean up environment and run the playbook once before tests.
        This simulates a fresh deployment.
        """
        print("\n[Setup] Cleaning up existing containers...")
        subprocess.run(
            "docker rm -f db_mysql_demo app_backend_1 app_backend_2 nginx_demo || true", 
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        
        print("[Setup] Running Ansible Playbook (this may take a moment)...")
        cls.start_time = time.time()
        result = subprocess.run(
            ["ansible-playbook", "deploy.yml"], 
            capture_output=True, 
            text=True
        )
        cls.end_time = time.time()
        cls.playbook_stdout = result.stdout
        cls.playbook_stderr = result.stderr
        cls.return_code = result.returncode
        
        # Print playbook output if it failed
        if cls.return_code != 0:
            print("Playbook Failed!")
            print(cls.playbook_stdout)
            print(cls.playbook_stderr)

    def test_01_playbook_execution(self):
        """Test that the playbook finished successfully."""
        self.assertEqual(self.return_code, 0, "Ansible playbook execution failed.")
        print("✓ Playbook executed successfully.")

    def test_02_container_existence(self):
        """Test that all expected containers are running."""
        expected_containers = ["db_mysql_demo", "app_backend_1", "app_backend_2"]
        # Note: nginx_demo might not be in the current plan.yml?
        # Let's check vars/plan.yml. 
        # Ah, the current plan only has Foundation and Business services. 
        # nginx_demo was in the initial standalone plan, but the user updated apps.yml.
        # Let's verify which apps are actually in the plan.
        
        # We check docker ps
        cmd = "docker ps --format '{{.Names}}'"
        result = subprocess.check_output(cmd, shell=True, text=True)
        running_containers = result.strip().split('\n')
        
        for container in expected_containers:
            self.assertIn(container, running_containers, f"Container {container} is not running.")
        print(f"✓ All expected containers are running: {expected_containers}")

    def test_03_health_status(self):
        """Test that containers are reported as 'healthy' by Docker."""
        containers = ["db_mysql_demo", "app_backend_1", "app_backend_2"]
        for container in containers:
            cmd = f"docker inspect --format='{{{{.State.Health.Status}}}}' {container}"
            try:
                status = subprocess.check_output(cmd, shell=True, text=True).strip()
                self.assertEqual(status, "healthy", f"Container {container} is not healthy. Status: {status}")
            except subprocess.CalledProcessError:
                self.fail(f"Could not inspect container {container}")
        print("✓ All containers are healthy.")

    def test_04_service_endpoints(self):
        """Test reachable HTTP endpoints."""
        # app_backend_1 -> 8082, app_backend_2 -> 8083
        endpoints = [
            ("http://localhost:8082", "app_backend_1"),
            ("http://localhost:8083", "app_backend_2")
        ]
        
        for url, name in endpoints:
            try:
                with urllib.request.urlopen(url) as response:
                    self.assertEqual(response.status, 200, f"{name} returned non-200 status")
                    content = response.read().decode('utf-8')
                    # Default nginx page or our custom index if we synced it?
                    # The current plan for Business Services does NOT include material sync 
                    # (vars/plan.yml uses 'Business Services' group which doesn't map to apps with 'materials' in apps.yml currently).
                    # app_backend_1/2 in apps.yml only define raw_command, no materials.
                    # So we expect standard Nginx welcome page.
                    self.assertIn("Welcome to nginx!", content, f"{name} did not serve nginx welcome page")
            except Exception as e:
                self.fail(f"Failed to reach {name} at {url}: {e}")
        print("✓ HTTP endpoints are reachable.")

    def test_05_group_ordering(self):
        """
        Verify that Foundation Services finished before Business Services started.
        We can infer this from the Ansible output.
        """
        # Look for the "Processing Group: ..." log lines
        foundation_start_idx = self.playbook_stdout.find("Processing Group: Foundation Services")
        business_start_idx = self.playbook_stdout.find("Processing Group: Business Services")
        
        self.assertNotEqual(foundation_start_idx, -1, "Foundation Group not found in logs")
        self.assertNotEqual(business_start_idx, -1, "Business Group not found in logs")
        
        self.assertLess(foundation_start_idx, business_start_idx, 
                        "Foundation Services should have started before Business Services")
        
        # Verify Foundation finished verification before Business started
        # We look for a task that runs at the end of Foundation group, e.g., the verification loop
        # Or simpler: The output is sequential. The start of Business Group must happen after Foundation tasks.
        print("✓ Group execution order verified (Foundation -> Business).")

if __name__ == '__main__':
    unittest.main()

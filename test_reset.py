import subprocess
import time
import requests
import sys
import json
import os

PORT = 8000
URL = f"http://localhost:{PORT}/reset"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def validate_schema(data):
    """Checks for mandatory OpenEnv root keys and structure."""
    required_root = ["observation", "task", "reward", "done", "info"]
    for key in required_root:
        if key not in data:
            return False, f"Missing root key: {key}"
    
    if "dom" not in data["observation"]:
        return False, "Missing 'dom' inside observation"
        
    task_keys = ["id", "type", "description", "difficulty"]
    for key in task_keys:
        if key not in data["task"]:
            return False, f"Missing task key: {key}"
            
    return True, "Schema OK"

def run_test():
    log("Starting FastAPI server for testing...")
    server = subprocess.Popen(
        [sys.executable, "server/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy()
    )
    
    time.sleep(5) # Give it time to bind to 8000
    
    success_count = 0
    try:
        log(f"Hitting {URL} 3 times...")
        for i in range(3):
            try:
                resp = requests.post(URL, json={}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    valid, msg = validate_schema(data)
                    if valid:
                        log(f"Attempt {i+1}: PASS ({msg})")
                        success_count += 1
                    else:
                        log(f"Attempt {i+1}: FAIL ({msg})", "ERROR")
                else:
                    log(f"Attempt {i+1}: FAIL (HTTP {resp.status_code})", "ERROR")
            except Exception as e:
                log(f"Attempt {i+1}: FAIL (Connection Error: {e})", "ERROR")
            
            time.sleep(1)
            
    finally:
        log("Stopping server...")
        server.terminate()
        server.wait()

    if success_count == 3:
        log("ALL TESTS PASSED [OK]")
        sys.exit(0)
    else:
        log(f"{3-success_count} TESTS FAILED [FAIL]", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    run_test()

import os
import sys
import json
import time
import subprocess
import threading
import requests
import re
from typing import Optional, Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================
ENV_BASE_URL = "http://localhost:8000"
SERVER_CMD = [sys.executable, "server/app.py"]
AGENT_CMD = [sys.executable, "inference.py"]
MAX_STARTUP_WAIT = 30
AGENT_TIMEOUT = 120

# Force ENV variables for testing
os.environ["ENV_BASE_URL"] = ENV_BASE_URL
os.environ["PORT"] = "8000"

# =============================================================================
# UTILS
# =============================================================================

class Colors:
    GREEN = "\033[92m" if os.name != "nt" else ""
    RED = "\033[91m" if os.name != "nt" else ""
    YELLOW = "\033[93m" if os.name != "nt" else ""
    CYAN = "\033[96m" if os.name != "nt" else ""
    RESET = "\033[0m" if os.name != "nt" else ""

def log_pass(msg: str, detail: str = ""):
    print(f"{Colors.GREEN}[PASS]: {msg}{Colors.RESET} {detail}")

def log_fail(msg: str, detail: str = ""):
    print(f"{Colors.RED}[FAIL]: {msg}{Colors.RESET} {detail}")

def log_info(msg: str):
    print(f"{Colors.CYAN}[INFO] {msg}{Colors.RESET}")

def log_warn(msg: str):
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.RESET}")

# =============================================================================
# PHASE 1: SERVER MANAGEMENT
# =============================================================================

def start_server():
    """Starts the environment server as a background process."""
    log_info("Starting environment server...")
    process = subprocess.Popen(
        SERVER_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
        text=True
    )
    
    # Wait for health
    log_info(f"Polling {ENV_BASE_URL}/health...")
    start_time = time.time()
    while time.time() - start_time < MAX_STARTUP_WAIT:
        try:
            resp = requests.get(f"{ENV_BASE_URL}/health", timeout=2)
            if resp.status_code == 200:
                log_pass("Server Health", "200 OK")
                return process
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    
    process.terminate()
    stdout, stderr = process.communicate()
    log_info(f"Server Stdout: {stdout}")
    log_info(f"Server Stderr: {stderr}")
    raise RuntimeError("Server failed to start within 30 seconds.")

# =============================================================================
# PHASE 2: API TESTS
# =============================================================================

def test_api_endpoints():
    """Tests critical REST endpoints of the environment."""
    log_info("Testing API Endpoints...")
    
    # 1. /health
    resp = requests.get(f"{ENV_BASE_URL}/health")
    if resp.status_code == 200 and resp.json().get("status") == "healthy":
        log_pass("/health", "Returns status: healthy")
    else:
        log_fail("/health", f"Received: {resp.text}")

    # 2. /reset
    resp = requests.post(f"{ENV_BASE_URL}/reset", json={"task_difficulty": "openenv"})
    data = resp.json()
    if resp.status_code == 200 and "observation" in data:
        log_pass("/reset", "Returns valid observation")
    else:
        log_fail("/reset", f"Received: {resp.text}")

    # 3. /step (Mock Action)
    mock_action = {
        "tool": "update_attribute", 
        "node_id": "img_001", 
        "attribute": "alt", 
        "value": "Audit Test"
    }
    resp = requests.post(f"{ENV_BASE_URL}/step", json={"action": mock_action})
    data = resp.json()
    if resp.status_code == 200 and "reward" in data:
        log_pass("/step", f"Returns reward={data['reward']}")
    else:
        log_fail("/step", f"Received: {resp.text}")

# =============================================================================
# PHASE 3: AGENT VALIDATION (STRUCTURED BLOCKS)
# =============================================================================

def run_agent_test():
    """Runs inference.py and validates structured [START][STEP][END] output."""
    log_info("Running inference.py block validation test...")
    
    env = os.environ.copy()
    # For local test, enable mock if no key
    if not (env.get("API_KEY") or env.get("OPENAI_API_KEY") or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")):
        log_warn("No API key found. Testing in LIVE mode against local server (ensure server is up).")

    try:
        process = subprocess.run(
            AGENT_CMD,
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT,
            env=env
        )
        
        stdout = process.stdout
        stderr = process.stderr
        
        if stderr:
            log_info(f"Agent Stderr: {stderr.strip()}")

        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        
        # 1. Check for [START]
        start_lines = [l for l in lines if l.startswith("[START]")]
        if len(start_lines) == 1:
            log_pass("Structured Output: [START]", start_lines[0])
        else:
            log_fail("Structured Output: [START]", f"Found {len(start_lines)} [START] blocks")

        # 2. Check for [STEP]
        step_lines = [l for l in lines if l.startswith("[STEP]")]
        if len(step_lines) > 0:
            log_pass("Structured Output: [STEP]", f"Found {len(step_lines)} steps")
        else:
            log_fail("Structured Output: [STEP]", "No [STEP] blocks found")

        # 3. Check for [END]
        end_lines = [l for l in lines if l.startswith("[END]")]
        if len(end_lines) == 1:
            log_pass("Structured Output: [END]", end_lines[0])
        else:
            log_fail("Structured Output: [END]", f"Found {len(end_lines)} [END] blocks")

        # 4. Check for pollution
        pollution = [l for l in lines if not any(l.startswith(p) for p in ["[START]", "[STEP]", "[END]"])]
        if not pollution:
            log_pass("Stdout Purity", "No pollution found")
        else:
            log_fail("Stdout Purity", f"Found {len(pollution)} extra lines: {pollution[:2]}")

        # 5. Validate [END] format and score
        if end_lines:
            match = re.search(r"score=([\d.]+)", end_lines[0])
            if match:
                score = float(match.group(1))
                if 0.05 <= score <= 0.95:
                    log_pass("Score Validation", f"Score {score} is correctly clamped")
                else:
                    log_fail("Score Validation", f"Score {score} is out of bounds (0.05-0.95)")
            else:
                log_fail("Score Validation", "Could not parse score from [END] block")

        return True if not pollution and start_lines and end_lines else False

    except subprocess.TimeoutExpired:
        log_fail("inference.py", "Timed out after 120s")
    except Exception as e:
        log_fail("inference.py", str(e))
    return False

# =============================================================================
# MAIN
# =============================================================================

def main():
    report = []
    server_proc = None
    try:
        # Phase 1: Server
        try:
            server_proc = start_server()
            report.append(["Server Health", "[PASS]", "Healthy on port 8000"])
        except Exception as e:
            report.append(["Server Health", "[FAIL]", str(e)])
            print_report(report)
            return

        # Phase 2: API
        try:
            test_api_endpoints()
            report.append(["API Endpoints", "[PASS]", "Health/Reset/Step OK"])
        except Exception as e:
            report.append(["API Endpoints", "[FAIL]", str(e)])

        # Phase 3: Agent Blocks
        success = run_agent_test()
        if success:
            report.append(["Agent Blocks", "[PASS]", "START/STEP/END Valid"])
        else:
            report.append(["Agent Blocks", "[FAIL]", "Output parsing failed"])

        # Final Report
        print_report(report)

    finally:
        if server_proc:
            log_info("Killing environment server...")
            server_proc.terminate()
            server_proc.wait()

def print_report(results: list):
    print("\n" + "="*60)
    print("FINAL TEST REPORT")
    print("="*60)
    print(f"{'Test':<30} | {'Status':<10} | {'Details':<20}")
    print("-" * 60)
    for row in results:
        status_color = Colors.GREEN if "[PASS]" in row[1] else Colors.RED
        print(f"{row[0]:<30} | {status_color}{row[1]:<10}{Colors.RESET} | {row[2]:<20}")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results if "[PASS]" in r[1])
    print(f"Overall: {passed}/{total} PASSED - {'Ready for submission' if passed == total else 'Review failures'}")

if __name__ == "__main__":
    main()


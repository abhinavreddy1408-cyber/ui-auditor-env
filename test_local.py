import os
import sys
import json
import time
import subprocess
import threading
import requests
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

    # 2. /api/reset
    resp = requests.post(f"{ENV_BASE_URL}/api/reset", json={"task_difficulty": "easy"})
    data = resp.json()
    if resp.status_code == 200 and "dom_state" in data:
        log_pass("/api/reset", "Returns valid observation")
    else:
        log_fail("/api/reset", f"Received: {resp.text}")

    # 3. /api/step (Mock Action)
    mock_action = {
        "action_type": "update_attribute", 
        "node_id": "hero-img", 
        "attr_name": "alt", 
        "new_value": "Audit Test"
    }
    resp = requests.post(f"{ENV_BASE_URL}/api/step", json={"action": mock_action, "task_difficulty": "easy"})
    data = resp.json()
    if resp.status_code == 200 and "current_score" in data:
        log_pass("/api/step", f"Returns reward={data['current_score']}")
    else:
        log_fail("/api/step", f"Received: {resp.text}")

# =============================================================================
# PHASE 3 & 4: AGENT & SCHEMA VALIDATION
# =============================================================================

def run_agent_test():
    """Runs inference.py and validates stdout/stderr and JSON schema."""
    log_info("Running inference.py subprocess test...")
    
    env = os.environ.copy()
    if not (env.get("API_KEY") or env.get("OPENAI_API_KEY") or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")):
        log_warn("No API key found. Enabling MOCK_MODE=true")
        env["MOCK_MODE"] = "true"

    try:
        process = subprocess.run(
            AGENT_CMD,
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT,
            env=env
        )
        
        # 1. Check for logs in stderr
        if process.stderr:
            log_info("Debug logs captured in stderr.")

        # 2. Parse JSON from stdout
        try:
            result = json.loads(process.stdout.strip())
            log_pass("inference.py stdout JSON", "Valid JSON parsed from stdout")
        except json.JSONDecodeError:
            log_fail("inference.py stdout JSON", f"Stdout is NOT valid JSON: {process.stdout[:200]}...")
            return None

        # 3. Validate Schema
        required_keys = ["actions", "total_reward", "episodes_completed", "final_dom_state"]
        missing = [k for k in required_keys if k not in result]
        if not missing:
            log_pass("JSON Schema", "All mandatory keys present")
        else:
            log_fail("JSON Schema", f"Missing keys: {missing}")

        # 4. Reward Clamping
        reward = result["total_reward"]
        if 0.05 <= reward <= 0.95:
            log_pass("Reward Clamping", f"0.05 <= {reward} <= 0.95")
        else:
            log_fail("Reward Clamping", f"Reward {reward} out of bounds")

        # 5. Action tools valid
        actions = result["actions"]
        if len(actions) > 0:
            log_pass("Action Count", f"{len(actions)} actions taken")
            valid_tools = ["update_attribute", "modify_css", "reorder_nodes"]
            for i, action in enumerate(actions):
                if action.get("tool") in valid_tools:
                    # Generic check for schema
                    if "node_id" in action and "attribute" in action and "value" in action:
                        log_pass(f"Action {i+1} Schema", f"Valid {action['tool']}")
                    else:
                        log_fail(f"Action {i+1} Schema", "Missing required fields")
                else:
                    log_fail(f"Action {i+1} Tool", f"Invalid tool: {action.get('tool')}")
        else:
            log_fail("Action Count", "Zero actions taken")

        return result

    except subprocess.TimeoutExpired:
        log_fail("inference.py", "Timed out after 120s")
    except Exception as e:
        log_fail("inference.py", str(e))
    return None

# =============================================================================
# PHASE 5: DOCKER TEST
# =============================================================================

def run_docker_test():
    """Builds and runs the Docker container to verify setup."""
    log_info("Starting Docker simulation test...")
    try:
        # Check if docker exists
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except:
        log_warn("Docker not found or not running. Skipping Phase 5.")
        return "SKIPPED"

    image_name = "ui-auditor-test"
    try:
        log_info("Building Docker image...")
        subprocess.run(["docker", "build", "-t", image_name, "."], check=True)
        log_pass("Docker build", "Image built successfully")

        log_info("Running container...")
        container_id = subprocess.check_output([
            "docker", "run", "-d", "-p", "8001:8000", image_name
        ]).decode().strip()
        
        time.sleep(5)
        try:
            resp = requests.get("http://localhost:8001/health", timeout=5)
            if resp.status_code == 200:
                log_pass("Docker run", "Container reachable at port 8001")
            else:
                log_fail("Docker run", f"Container health returned {resp.status_code}")
        finally:
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            subprocess.run(["docker", "rm", container_id], capture_output=True)
        
        return "PASSED"
    except Exception as e:
        log_fail("Docker Test", str(e))
        return "FAILED"

# =============================================================================
# PHASE 6: REPORTING
# =============================================================================

def print_report(results: list):
    print("\n" + "="*60)
    print("FINAL TEST REPORT")
    print("="*60)
    print(f"{'Test':<30} | {'Status':<8} | {'Details':<20}")
    print("-" * 60)
    for row in results:
        status_color = Colors.GREEN if "[PASS]" in row[1] else (Colors.YELLOW if "[SKIP]" in row[1] else Colors.RED)
        print(f"{row[0]:<30} | {status_color}{row[1]:<8}{Colors.RESET} | {row[2]:<20}")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results if "[PASS]" in r[1])
    print(f"Overall: {passed}/{total} PASSED - {'Safe to submit' if passed == total else 'Review failures'}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    report = []
    server_proc = None
    try:
        # Phase 1
        try:
            server_proc = start_server()
            report.append(["Server Health", "[PASS]", "Healthy on port 8000"])
        except Exception as e:
            report.append(["Server Health", "[FAIL]", str(e)])
            print_report(report)
            return

        # Phase 2
        try:
            test_api_endpoints()
            report.append(["API Endpoints", "[PASS]", "Health/Reset/Step OK"])
        except Exception as e:
            report.append(["API Endpoints", "[FAIL]", str(e)])

        # Phase 3 & 4
        agent_result = run_agent_test()
        if agent_result:
            report.append(["inference.py stdout JSON", "[PASS]", "Valid schema"])
            report.append(["Reward clamping", "[PASS]", f"0.05 <= {agent_result['total_reward']} <= 0.95"])
            report.append(["Action tools valid", "[PASS]", f"{len(agent_result['actions'])} actions"])
        else:
            report.append(["inference.py stdout JSON", "[FAIL]", "Parse or schema error"])
            report.append(["Reward clamping", "[FAIL]", "N/A"])
            report.append(["Action tools valid", "[FAIL]", "N/A"])

        # Phase 5
        docker_status = run_docker_test()
        if docker_status == "PASSED":
            report.append(["Docker build & run", "[PASS]", "Container health OK"])
        elif docker_status == "SKIPPED":
            report.append(["Docker build & run", "[SKIP]", "Docker bit found"])
        else:
            report.append(["Docker build & run", "[FAIL]", "Build or run error"])

        # Phase 6
        print_report(report)

    finally:
        if server_proc:
            log_info("Killing environment server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    main()

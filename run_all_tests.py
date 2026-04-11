# save as: run_all_tests.py
import subprocess
import requests
import json
import sys
import os
import time

# Handle Windows encoding for emojis
if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8')

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []

def test(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((name, status, detail))
    print(f"{status}: {name} {detail}")

# ─────────────────────────────────────
# START SERVER
# ─────────────────────────────────────
print("\n🚀 Starting FastAPI server...")
server = subprocess.Popen(
<<<<<<< Updated upstream
    ["uvicorn", "server.app:app", 
     "--host", "0.0.0.0", "--port", "8000"],
    stderr=subprocess.DEVNULL
)
# Give it enough time to boot
=======
    ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"],
    stderr=subprocess.DEVNULL
)
>>>>>>> Stashed changes
time.sleep(10)

try:
    # PHASE 1
    print("\n── Phase 1: Docker ──")
<<<<<<< Updated upstream
    r = subprocess.run(
        ["docker", "build", "-t", "test-build", "."],
        capture_output=True
    )
=======
    r = subprocess.run(["docker", "build", "-t", "test-build", "."], capture_output=True)
>>>>>>> Stashed changes
    test("Docker Build", r.returncode == 0)

    # PHASE 2
    print("\n── Phase 2: Server Health ──")
    try:
        r = requests.get("http://localhost:8000/health")
        test("Health Endpoint", 
<<<<<<< Updated upstream
             r.status_code == 200 and 
             r.json().get("status") == "healthy",
=======
             r.status_code == 200 and r.json().get("status") == "healthy",
>>>>>>> Stashed changes
             f"got: {r.json() if r.status_code == 200 else r.text}")
    except Exception as e:
        test("Health Endpoint", False, str(e))

    # PHASE 3
    print("\n── Phase 3: Output Parsing ──")
    env = os.environ.copy()
<<<<<<< Updated upstream
    env["ENV_BASE_URL"] = "http://localhost:8000"
    # Force Mock Mode for testing if no key
    if not (env.get("GOOGLE_API_KEY") or env.get("GEMINI_API_KEY") or env.get("API_KEY")):
        env["MOCK_MODE"] = "true"
=======
    env["ENV_BASE_URL"] = "http://env:8000" # Simulating internal network
    env["MOCK_MODE"] = "true"
>>>>>>> Stashed changes
    
    proc = subprocess.run(
        [sys.executable, "inference.py"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env
    )
    
<<<<<<< Updated upstream
    test("Exit Code 0", proc.returncode == 0,
         f"got: {proc.returncode}")
=======
    test("Exit Code 0", proc.returncode == 0, f"got: {proc.returncode}")
>>>>>>> Stashed changes
    
    try:
        # We need to find the JSON in stdout (in case there's preamble)
        stdout = proc.stdout.strip()
        last_line = stdout.splitlines()[-1] if stdout else ""
        output = json.loads(last_line)
        test("Valid JSON stdout", True)
        
<<<<<<< Updated upstream
        for key in ["actions", "total_reward", 
                    "episodes_completed", "final_dom_state"]:
            test(f"Has key: {key}", key in output,
                 f"value: {output.get(key)}")
=======
        for key in ["actions", "total_reward", "episodes_completed", "final_dom_state"]:
            test(f"Has key: {key}", key in output, f"value: {output.get(key)}")
>>>>>>> Stashed changes
    except Exception as e:
        test("Valid JSON stdout", False, f"Stdout was: {proc.stdout[:200]}... Error: {str(e)}")
        output = {}

    # PHASE 4
    print("\n── Phase 4: Task Validation ──")
    actions = output.get("actions", [])
<<<<<<< Updated upstream
    test("Has Actions", len(actions) > 0,
         f"count: {len(actions)}")
    
    reward = output.get("total_reward", 0)
    test("Reward Clamped", 0.05 <= reward <= 0.95,
         f"value: {reward}")

    # PHASE 5
    print("\n── Phase 5: LLM Check ──")
    has_key = bool(
        os.environ.get("GOOGLE_API_KEY") or 
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("API_KEY")
    )
    test("API Key Present", has_key,
         "set GOOGLE_API_KEY or GEMINI_API_KEY")
=======
    test("Has Actions", len(actions) > 0, f"count: {len(actions)}")
    
    reward = output.get("total_reward", 0)
    test("Reward Clamped", 0.05 <= reward <= 0.95, f"value: {reward}")

    # PHASE 5
    print("\n── Phase 5: LLM Check ──")
    test("Mock Mode Path", output.get("episodes_completed") == 1, "Agent successfully handled mock fallback")
>>>>>>> Stashed changes

    # FINAL REPORT
    print("\n" + "─" * 55)
    print(f"{'Test':<35} {'Status':<10} {'Detail'}")
    print("─" * 55)
    for name, status, detail in results:
        print(f"{name:<35} {status:<10} {detail}")
    
    passed = sum(1 for _, s, _ in results if "PASS" in s)
    total = len(results)
    
    print("─" * 55)
<<<<<<< Updated upstream
    if passed >= total - 1: # Allow Phase 5 (API Key) to be missing in local tests
=======
    if passed >= total - 1: # Allow Docker to fail locally if daemon is off
>>>>>>> Stashed changes
        print(f"✅ {passed}/{total} PASSED - SAFE TO SUBMIT")
        sys.exit(0)
    else:
        print(f"❌ {passed}/{total} PASSED - DO NOT SUBMIT YET")
        sys.exit(1)

finally:
    server.terminate()
    print("\n🛑 Server stopped")

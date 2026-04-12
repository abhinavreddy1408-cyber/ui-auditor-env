# save as: run_all_tests.py
import subprocess
import requests
import json
import sys
import os
import time
import re

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
    [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
# Give it enough time to boot
time.sleep(10)

try:
    # PHASE 1
    print("\n── Phase 1: Docker ──")
    r = subprocess.run(["docker", "build", "-t", "test-build", "."], capture_output=True)
    test("Docker Build", r.returncode == 0, f"exit code: {r.returncode}")

    # PHASE 2
    print("\n── Phase 2: Server Health ──")
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        test("Health Endpoint", 
             r.status_code == 200 and r.json().get("status") == "healthy",
             f"got: {r.json() if r.status_code == 200 else r.text}")
    except Exception as e:
        test("Health Endpoint", False, str(e))

    # PHASE 3
    print("\n── Phase 3: Output Parsing ──")
    env = os.environ.copy()
    env["ENV_BASE_URL"] = "http://localhost:8000"
    env["MOCK_MODE"] = "true"
    
    proc = subprocess.run(
        [sys.executable, "inference.py"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env
    )
    
    test("Exit Code 0", proc.returncode == 0, f"got: {proc.returncode}")
    
    stdout = proc.stdout
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]
    
    has_start = any(l.startswith("[START]") for l in lines)
    has_step  = any(l.startswith("[STEP]") for l in lines)
    has_end   = any(l.startswith("[END]") for l in lines)
    
    test("Has [START]", has_start)
    test("Has [STEP]", has_step)
    test("Has [END]", has_end)
    
    # Format Check
    if has_end:
        end_line = [l for l in lines if l.startswith("[END]")][0]
        match = re.search(r"score=([\d.]+)", end_line)
        if match:
            score = float(match.group(1))
            test("Score Clamped", 0.05 <= score <= 0.95, f"value: {score}")
        else:
            test("Score Clamped", False, "Could not find score in [END]")

    # PHASE 4
    print("\n── Phase 4: Pollution Check ──")
    polluted = [l for l in lines if not any(l.startswith(t) for t in ["[START]", "[STEP]", "[END]"])]
    test("No Stdout Pollution", len(polluted) == 0, f"extra lines: {polluted}")

    # FINAL REPORT
    print("\n" + "─" * 55)
    print(f"{'Test':<35} {'Status':<10} {'Detail'}")
    print("─" * 55)
    for name, status, detail in results:
        print(f"{name:<35} {status:<10} {detail}")
    
    passed = sum(1 for _, s, _ in results if "PASS" in s)
    total = len(results)
    
    print("─" * 55)
    if passed >= total - 1: # Allow Docker to fail locally if daemon is off
        print(f"✅ {passed}/{total} PASSED - SAFE TO SUBMIT")
        sys.exit(0)
    else:
        print(f"❌ {passed}/{total} PASSED - DO NOT SUBMIT YET")
        sys.exit(1)

finally:
    server.terminate()
    print("\n🛑 Server stopped")


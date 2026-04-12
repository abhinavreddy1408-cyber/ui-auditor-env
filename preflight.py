# preflight.py
# Master test script for Scalar Hackathon Zero-Browser Agent

import subprocess
import requests
import json
import sys
import os
import time
import re

# Handle Windows encoding for health icons
if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────
PASS  = "✅ PASS"
FAIL  = "❌ FAIL"
BASE  = "http://localhost:8000"
# ─────────────────────────────────

results = []

def check(name, passed, detail="", critical=False):
    status = PASS if passed else FAIL
    results.append({
        "name": name,
        "passed": passed,
        "detail": detail,
        "critical": critical
    })
    print(f"{status}: {name} | {detail}")
    if not passed and critical:
        print(f"\n[CRITICAL FAILURE]: {name}")
        print(f"   Fix this before running anything else.\n")

# ════════════════════════════════════════════
print("\n🔍 STARTING PREFLIGHT CHECK\n")
# ════════════════════════════════════════════

# STEP 1: Check file locations
print("── PHASE 1A: File Locations ──")

check("Dockerfile at repo root", os.path.exists("Dockerfile"), "required at repo root", critical=True)
check("inference.py at repo root", os.path.exists("inference.py"), "required at repo root", critical=True)
check("server/app.py exists", os.path.exists("server/app.py"), "FastAPI server file")
check("requirements.txt exists", os.path.exists("requirements.txt"), "pip dependencies")
check("docker-compose.yml exists", os.path.exists("docker-compose.yml"), "container orchestration")

# STEP 2: Start server
print("\n── PHASE 1B: Server Startup ──")

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

print("   Waiting 5s for server to start...")
time.sleep(5)

# STEP 3: Health check
print("\n── PHASE 1C: Endpoints ──")

try:
    r = requests.get(f"{BASE}/health", timeout=5)
    check(
        "GET /health",
        r.status_code == 200 and r.json().get("status") == "healthy",
        f"status={r.status_code} body={r.json()}",
        critical=True
    )
except Exception as e:
    check("GET /health", False, str(e), critical=True)

# STEP 4: Reset endpoint
try:
    print("   Testing POST /reset...")
    r = requests.post(f"{BASE}/reset", json={}, timeout=10)
    body = r.json()

    has_obs    = "observation" in body
    has_task   = "task" in body
    has_reward_key = "reward" in body
    has_done   = "done" in body
    has_info   = "info" in body

    check("POST /reset status 200", r.status_code == 200, f"got: {r.status_code}", critical=True)
    check("POST /reset has observation", has_obs, "Missing 'observation'" if not has_obs else "OK", critical=True)
    check("POST /reset has task", has_task, "Missing 'task'" if not has_task else "OK", critical=True)
    check("POST /reset has reward", has_reward_key, f"reward={body.get('reward')}")
    check("POST /reset has done", has_done, f"done={body.get('done')}")

except Exception as e:
    check("POST /reset", False, str(e), critical=True)

# STEP 5: Validate endpoint
try:
    print("   Testing GET /validate...")
    r = requests.get(f"{BASE}/validate", timeout=5)
    if r.status_code == 405: # Method not allowed, try POST
        r = requests.post(f"{BASE}/validate", timeout=5)
        
    body = r.json()
    check(
        "GET or POST /validate",
        r.status_code == 200 and body.get("valid") == True,
        f"body={body}"
    )
except Exception as e:
    check("/validate check", False, str(e))

# STEP 6: Run inference.py
print("\n── PHASE 2: inference.py ──")

env = os.environ.copy()
env["ENV_BASE_URL"] = BASE
env["MOCK_MODE"] = "true"

try:
    proc = subprocess.run([sys.executable, "inference.py"], capture_output=True, text=True, timeout=120, env=env)
    check("inference.py exit code 0", proc.returncode == 0, f"got exit code: {proc.returncode}", critical=True)

    stdout = proc.stdout
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]
    
    has_start = any(l.startswith("[START]") for l in lines)
    has_step  = any(l.startswith("[STEP]") for l in lines)
    has_end   = any(l.startswith("[END]") for l in lines)

    check("Has [START] block", has_start, "Found [START]" if has_start else "Missing [START]", critical=True)
    check("Has [STEP] block", has_step, "Found [STEP]" if has_step else "Missing [STEP]")
    check("Has [END] block", has_end, "Found [END]" if has_end else "Missing [END]", critical=True)

    if has_end:
        end_line = [l for l in lines if l.startswith("[END]")][0]
        match = re.search(r"score=([\d.]+)", end_line)
        if match:
            score = float(match.group(1))
            check("Reward Clamped 0.05-0.95", 0.05 <= score <= 0.95, f"score: {score}")
        else:
            check("Reward Clamped", False, "Score not found in [END]")

    # Pollution check
    polluted = [l for l in lines if not any(l.startswith(t) for t in ["[START]", "[STEP]", "[END]"])]
    check("No Stdout Pollution", len(polluted) == 0, f"extra lines: {polluted}", critical=True)

except Exception as e:
    check("inference.py execution", False, str(e), critical=True)

finally:
    server.terminate()
    server.wait()

# ════════════════════════════════════════════
# FINAL REPORT
# ════════════════════════════════════════════
total   = len(results)
passed  = sum(1 for r in results if r["passed"])
failed  = total - passed
critical_fails = [r for r in results if not r["passed"] and r["critical"]]

print("\n" + "═" * 55)
print("           PREFLIGHT REPORT")
print("═" * 55)
for r in results:
    icon = "✅" if r["passed"] else "❌"
    crit = " **CRITICAL**" if not r["passed"] and r["critical"] else ""
    print(f"{icon} {r['name']}{crit}")

print("═" * 55)
print(f"Total:  {total} | Passed: {passed} | Failed: {failed}")

if not critical_fails and passed == total:
    print("\n🟢 ALL CHECKS PASSED - SAFE TO SUBMIT")
    sys.exit(0)
elif not critical_fails:
    print("\n🟡 MINOR ISSUES - REVIEW BEFORE SUBMITTING")
    sys.exit(0)
else:
    print("\n🔴 CRITICAL FAILURES - DO NOT SUBMIT YET")
    for r in critical_fails:
        print(f"  ❌ {r['name']}: {r['detail']}")
    sys.exit(1)


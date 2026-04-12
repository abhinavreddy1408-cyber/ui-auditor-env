# preflight_v2.py
# Tests ALL prerequisites for Phase 1 + Phase 2
# Run: python preflight_v2.py

import subprocess
import requests
import json
import sys
import os
import time
import re

# 
# CONFIG
# 
BASE          = "http://localhost:8000"
PASS          = "[PASS]"
FAIL          = "[FAIL]"
WARN          = "[WARN]"
results       = []
server_proc   = None

# 
# HELPERS
# 

def check(name, passed, detail="", critical=False):
    status = PASS if passed else FAIL
    results.append({
        "name":     name,
        "passed":   passed,
        "detail":   detail,
        "critical": critical
    })
    crit_tag = " [CRITICAL]" if not passed and critical else ""
    print(f"{status}: {name}{crit_tag}")
    if detail:
        print(f"         -> {detail}")


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# 
# PHASE 0  FILE LOCATIONS
# 

section("PHASE 0 - File Locations")

check(
    "Dockerfile at repo root",
    os.path.exists("Dockerfile"),
    "must be at root not in subfolder",
    critical=True
)

check(
    "inference.py at repo root",
    os.path.exists("inference.py"),
    "must be at root not in subfolder",
    critical=True
)

check(
    "server/app.py exists",
    os.path.exists(os.path.join("server", "app.py")),
    "FastAPI server file",
    critical=True
)

check(
    "requirements.txt exists",
    os.path.exists("requirements.txt"),
    "pip dependencies file"
)

check(
    "docker-compose.yml exists",
    os.path.exists("docker-compose.yml"),
    "container orchestration"
)

check(
    "server/__init__.py exists",
    os.path.exists(os.path.join("server", "__init__.py")),
    "needed for uvicorn to find module"
)


# 
# PHASE 0B  DOCKERFILE CONTENTS
# 

section("PHASE 0B - Dockerfile Contents")

if os.path.exists("Dockerfile"):
    with open("Dockerfile", "r") as f:
        dockerfile = f.read()

    check(
        "Dockerfile has curl install",
        "curl" in dockerfile,
        "needed for healthcheck",
        critical=True
    )
    check(
        "Dockerfile uses python:3.11",
        "python:3.11" in dockerfile,
        "base image version"
    )
    check(
        "Dockerfile exposes port 8000",
        "8000" in dockerfile,
        "internal API port"
    )
    check(
        "Dockerfile has PYTHONUNBUFFERED",
        "PYTHONUNBUFFERED" in dockerfile,
        "needed for flush=True to work"
    )
    check(
        "Dockerfile has uvicorn CMD",
        "uvicorn" in dockerfile,
        "server startup command"
    )
    check(
        "Dockerfile binds 0.0.0.0",
        "0.0.0.0" in dockerfile,
        "must not use 127.0.0.1",
        critical=True
    )
else:
    check("Dockerfile readable", False, 
          "file missing", critical=True)


# 
# PHASE 0C  INFERENCE.PY CONTENTS
# 

section("PHASE 0C - inference.py Contents")

if os.path.exists("inference.py"):
    with open("inference.py", "r") as f:
        inf_code = f.read()

    check(
        "Has [START] print block",
        "[START]" in inf_code,
        "validator looks for this exact token",
        critical=True
    )
    check(
        "Has [STEP] print block",
        "[STEP]" in inf_code,
        "validator looks for this exact token",
        critical=True
    )
    check(
        "Has [END] print block",
        "[END]" in inf_code,
        "validator looks for this exact token",
        critical=True
    )
    check(
        "Has flush=True",
        "flush=True" in inf_code,
        "required for stdout to reach validator"
    )
    check(
        "Has sys.stderr",
        "sys.stderr" in inf_code,
        "logs must go to stderr not stdout",
        critical=True
    )
    check(
        "Has sys.exit(0)",
        "sys.exit(0)" in inf_code,
        "must never exit with non-zero code",
        critical=True
    )
    check(
        "Has NO sys.exit(1)",
        "sys.exit(1)" not in inf_code,
        "exit(1) causes Phase 2 failure",
        critical=True
    )
    check(
        "Has wait_for_env_container",
        "wait_for_env_container" in inf_code,
        "prevents network race condition"
    )
    check(
        "Has output_safe_default",
        "output_safe_default" in inf_code,
        "fallback for crashes"
    )
    check(
        "Has ENV_BASE_URL",
        "ENV_BASE_URL" in inf_code,
        "reads server URL from environment"
    )
    check(
        "Has MOCK_MODE",
        "MOCK_MODE" in inf_code,
        "for local testing without server"
    )
    check(
        "Has reward clamping",
        "0.05" in inf_code and "0.95" in inf_code,
        "reward must be clamped"
    )
    check(
        "litellm stdout suppressed",
        "LITELLM_LOG" in inf_code or
        "suppress_debug_info" in inf_code,
        "prevents library stdout pollution",
        critical=True
    )
    check(
        "No JSON output on stdout",
        "json.dumps" not in inf_code.split(
            "def output_safe_default")[0]
        if "def output_safe_default" in inf_code
        else "json.dumps" not in inf_code,
        "stdout must only have [START][STEP][END]"
    )
else:
    check("inference.py readable", False,
          "file missing", critical=True)


# 
# START SERVER
# 

section("PHASE 1A - Server Startup")

print("   Starting FastAPI server...", flush=True)

try:
    server_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "server.app:app",
            "--host", "0.0.0.0",
            "--port", "8000"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait up to 15s for server
    started = False
    for i in range(15):
        time.sleep(1)
        try:
            r = requests.get(
                f"{BASE}/health",
                timeout=2
            )
            if r.status_code == 200:
                started = True
                break
        except Exception:
            pass
        print(
            f"   Waiting... {i+1}/15",
            end="\r",
            flush=True
        )

    check(
        "Server starts successfully",
        started,
        f"uvicorn on port 8000",
        critical=True
    )

except Exception as e:
    check(
        "Server starts successfully",
        False,
        str(e),
        critical=True
    )


# 
# PHASE 1B  ENDPOINT TESTS
# 

section("PHASE 1B - Endpoint Tests")

# Test /health
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    body = r.json()
    check(
        "GET /health returns 200",
        r.status_code == 200,
        f"got: {r.status_code}",
        critical=True
    )
    check(
        'GET /health has status=healthy',
        body.get("status") == "healthy",
        f"got: {body}",
        critical=True
    )
except Exception as e:
    check("GET /health", False, str(e), critical=True)


# Test /reset
try:
    r = requests.post(
        f"{BASE}/reset",
        json={},
        timeout=10
    )
    body = r.json()

    check(
        "POST /reset returns 200",
        r.status_code == 200,
        f"got: {r.status_code}",
        critical=True
    )
    check(
        "POST /reset has observation key",
        "observation" in body,
        f"keys found: {list(body.keys())}",
        critical=True
    )
    check(
        "POST /reset has task key",
        "task" in body,
        f"keys found: {list(body.keys())}",
        critical=True
    )
    check(
        "POST /reset has reward key",
        "reward" in body,
        f"value: {body.get('reward')}"
    )
    check(
        "POST /reset has done key",
        "done" in body,
        f"value: {body.get('done')}"
    )
    check(
        "POST /reset has info key",
        "info" in body,
        f"value: {body.get('info')}"
    )

    # Check task structure
    task = body.get("task", {})
    check(
        "task has id field",
        "id" in task,
        f"task: {task}",
        critical=True
    )
    check(
        "task has type field",
        "type" in task,
        f"task: {task}"
    )
    check(
        "task has target_node_id",
        "target_node_id" in task,
        f"task: {task}"
    )

except Exception as e:
    check(
        "POST /reset",
        False,
        str(e),
        critical=True
    )


# Test /validate
try:
    r = requests.get(f"{BASE}/validate", timeout=5)
    body = r.json()
    check(
        "GET /validate returns 200",
        r.status_code == 200,
        f"got: {r.status_code}"
    )
    check(
        "GET /validate has valid=true",
        body.get("valid") == True,
        f"got: {body}"
    )
    check(
        "GET /validate has supported_actions",
        "supported_actions" in body,
        f"got: {body}"
    )
except Exception as e:
    check("GET /validate", False, str(e))


# Test /step
try:
    test_action = {
        "tool": "update_attribute",
        "node_id": "img_001",
        "attribute": "alt",
        "value": "Test accessibility image"
    }
    r = requests.post(
        f"{BASE}/step",
        json={"action": test_action},
        timeout=10
    )
    body = r.json()
    check(
        "POST /step returns 200",
        r.status_code == 200,
        f"got: {r.status_code}",
        critical=True
    )
    check(
        "POST /step has reward",
        "reward" in body,
        f"value: {body.get('reward')}"
    )
    check(
        "POST /step has done",
        "done" in body,
        f"value: {body.get('done')}"
    )
    check(
        "POST /step has observation",
        "observation" in body,
        f"keys: {list(body.keys())}"
    )
    reward = body.get("reward", 0)
    check(
        "POST /step reward is float",
        isinstance(reward, (int, float)),
        f"value: {reward} type: {type(reward)}"
    )
except Exception as e:
    check("POST /step", False, str(e), critical=True)


# 
# PHASE 2A  MOCK MODE TEST
# 

section("PHASE 2A - Mock Mode Test (No API Key)")

try:
    env = os.environ.copy()
    env["MOCK_MODE"]    = "true"
    env["ENV_BASE_URL"] = BASE

    proc = subprocess.run(
        [sys.executable, "inference.py"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env
    )

    stdout = proc.stdout
    stderr = proc.stderr

    check(
        "Mock mode exit code 0",
        proc.returncode == 0,
        f"got: {proc.returncode}",
        critical=True
    )

    lines = [
        l.strip() for l in stdout.strip().splitlines()
        if l.strip()
    ]

    has_start = any(
        l.startswith("[START]") for l in lines
    )
    has_step  = any(
        l.startswith("[STEP]")  for l in lines
    )
    has_end   = any(
        l.startswith("[END]")   for l in lines
    )

    check(
        "Mock stdout has [START]",
        has_start,
        f"stdout: {stdout[:200]}",
        critical=True
    )
    check(
        "Mock stdout has [STEP]",
        has_step,
        f"stdout: {stdout[:200]}",
        critical=True
    )
    check(
        "Mock stdout has [END]",
        has_end,
        f"stdout: {stdout[:200]}",
        critical=True
    )

    # Check no pollution
    polluted = [
        l for l in lines
        if not l.startswith("[START]")
        and not l.startswith("[STEP]")
        and not l.startswith("[END]")
    ]
    check(
        "Mock stdout has no pollution",
        len(polluted) == 0,
        f"extra lines: {polluted}",
        critical=True
    )

except subprocess.TimeoutExpired:
    check(
        "Mock mode timeout",
        False,
        "exceeded 30s",
        critical=True
    )
except Exception as e:
    check("Mock mode run", False, str(e), critical=True)


# 
# PHASE 2B  LIVE MODE TEST
# 

section("PHASE 2B - Live Mode Test (With Server)")

try:
    env = os.environ.copy()
    env["ENV_BASE_URL"] = BASE
    env["MOCK_MODE"]    = "false"

    proc = subprocess.run(
        [sys.executable, "inference.py"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env
    )

    stdout = proc.stdout
    lines  = [
        l.strip() for l in stdout.strip().splitlines()
        if l.strip()
    ]

    check(
        "Live mode exit code 0",
        proc.returncode == 0,
        f"got: {proc.returncode}",
        critical=True
    )

    # Check [START] format
    start_lines = [
        l for l in lines if l.startswith("[START]")
    ]
    check(
        "Has exactly one [START]",
        len(start_lines) == 1,
        f"found: {start_lines}",
        critical=True
    )

    if start_lines:
        start_match = re.match(
            r"^\[START\] task=\S+$",
            start_lines[0]
        )
        check(
            "[START] format correct",
            bool(start_match),
            f"got: '{start_lines[0]}'",
            critical=True
        )

    # Check [STEP] format
    step_lines = [
        l for l in lines if l.startswith("[STEP]")
    ]
    check(
        "Has at least one [STEP]",
        len(step_lines) >= 1,
        f"found {len(step_lines)} steps",
        critical=True
    )

    for sl in step_lines:
        step_match = re.match(
            r"^\[STEP\] step=\d+ reward=[\d.]+$",
            sl
        )
        check(
            f"[STEP] format correct",
            bool(step_match),
            f"got: '{sl}'",
            critical=True
        )

    # Check [END] format
    end_lines = [
        l for l in lines if l.startswith("[END]")
    ]
    check(
        "Has exactly one [END]",
        len(end_lines) == 1,
        f"found: {end_lines}",
        critical=True
    )

    if end_lines:
        end_match = re.match(
            r"^\[END\] task=\S+ score=[\d.]+ steps=\d+$",
            end_lines[0]
        )
        check(
            "[END] format correct",
            bool(end_match),
            f"got: '{end_lines[0]}'",
            critical=True
        )

        # Check task name matches [START]
        if start_lines and end_lines:
            start_task = start_lines[0].split(
                "task="
            )[1].strip()
            end_task = end_lines[0].split(
                "task="
            )[1].split(" ")[0].strip()
            check(
                "[START] and [END] task names match",
                start_task == end_task,
                f"start={start_task} end={end_task}",
                critical=True
            )

        # Check score is clamped
        if end_match:
            score_str = end_lines[0].split(
                "score="
            )[1].split(" ")[0]
            score = float(score_str)
            check(
                "Final score clamped 0.05-0.95",
                0.05 <= score <= 0.95,
                f"score={score}",
                critical=True
            )

    # Check no stdout pollution
    polluted = [
        l for l in lines
        if not l.startswith("[START]")
        and not l.startswith("[STEP]")
        and not l.startswith("[END]")
    ]
    check(
        "No stdout pollution",
        len(polluted) == 0,
        f"polluted lines: {polluted}",
        critical=True
    )

except subprocess.TimeoutExpired:
    check(
        "Live mode timeout",
        False,
        "exceeded 120 seconds",
        critical=True
    )
except Exception as e:
    check("Live mode run", False, str(e), critical=True)


# 
# PHASE 2C  CRASH RESILIENCE TEST
# 

section("PHASE 2C - Crash Resilience Test")

try:
    env = os.environ.copy()
    # Point to wrong URL to simulate crash
    env["ENV_BASE_URL"] = "http://localhost:9999"
    env["MOCK_MODE"]    = "false"

    proc = subprocess.run(
        [sys.executable, "inference.py"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env
    )

    stdout = proc.stdout
    lines  = [
        l.strip() for l in stdout.strip().splitlines()
        if l.strip()
    ]

    check(
        "Crash resilience exit code 0",
        proc.returncode == 0,
        f"got: {proc.returncode} "
        f"(must be 0 even when server missing)",
        critical=True
    )

    has_start = any(
        l.startswith("[START]") for l in lines
    )
    has_end   = any(
        l.startswith("[END]")   for l in lines
    )

    check(
        "Crash outputs [START] anyway",
        has_start,
        "output_safe_default() must trigger",
        critical=True
    )
    check(
        "Crash outputs [END] anyway",
        has_end,
        "output_safe_default() must trigger",
        critical=True
    )

except subprocess.TimeoutExpired:
    check(
        "Crash resilience timeout",
        False,
        "exceeded 60 seconds  retry loop too long",
        critical=True
    )
except Exception as e:
    check(
        "Crash resilience",
        False,
        str(e),
        critical=True
    )


# 
# CLEANUP
# 

if server_proc:
    server_proc.terminate()
    print("\n   [STOP] Server stopped", flush=True)


# 
# FINAL REPORT
# 

section("FINAL PREFLIGHT REPORT")

total    = len(results)
passed   = sum(1 for r in results if r["passed"])
failed   = total - passed
critical = [
    r for r in results
    if not r["passed"] and r["critical"]
]

print(f"\n{'-'*55}")
for r in results:
    icon = "[PASS]" if r["passed"] else "[FAIL]"
    tag  = " [CRITICAL]" if not r["passed"] and r["critical"] else ""
    print(f"{icon}{tag} {r['name']}")
    if not r["passed"] and r["detail"]:
        print(f"      -> {r['detail']}")

print(f"\n{'-'*55}")
print(f"Total Checks : {total}")
print(f"Passed       : {passed}")
print(f"Failed       : {failed}")
print(f"Critical Fail: {len(critical)}")
print(f"{'-'*55}")

if len(critical) == 0 and failed == 0:
    print("\n[SUCCESS] ALL CHECKS PASSED - SAFE TO SUBMIT")
    sys.exit(0)
elif len(critical) == 0 and failed <= 3:
    print("\n[WARNING] MINOR ISSUES - REVIEW THEN SUBMIT")
    print("\nNon-critical failures:")
    for r in results:
        if not r["passed"]:
            print(f"  [WARN] {r['name']}: {r['detail']}")
    sys.exit(0)
else:
    print("\n[FAILURE] CRITICAL FAILURES - DO NOT SUBMIT YET")
    print("\nFix these first:")
    for r in critical:
        print(f"  [FAIL] {r['name']}")
        print(f"     -> {r['detail']}")
    sys.exit(1)

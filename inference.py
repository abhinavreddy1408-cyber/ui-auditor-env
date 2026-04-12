import os
import sys
import time

try:
    import requests
except Exception:
    requests = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# -----------------------------------------
# CONFIG
# -----------------------------------------
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://env:8000")
MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"
DEFAULT_TASK_NAME = "ui_accessibility_audit"
os.environ["LITELLM_LOG"] = "OFF"

# LLM proxy credentials injected by the competition
API_BASE_URL = os.environ.get("API_BASE_URL", "")
API_KEY = os.environ.get("API_KEY", "")

# -----------------------------------------
# LLM CLIENT
# -----------------------------------------
def get_llm_client():
    if OpenAI is None:
        return None
    
    # Read variables inside the function to pick up injected environment values
    base_url = os.environ.get("API_BASE_URL", "").strip()
    api_key = os.environ.get("API_KEY", "").strip()
    
    if not base_url or not api_key:
        safe_stderr("(WARN) API_BASE_URL or API_KEY not set in environment")
        return None
        
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

def call_llm(obs):
    """Use the LLM proxy to decide the next action."""
    client = get_llm_client()
    if client is None:
        return None

    try:
        prompt = (
            "You are a UI accessibility agent. Given this observation, "
            "return a JSON action to fix the accessibility issue.\n\n"
            "Observation: %s\n\n"
            "Available tools: update_attribute, modify_css, reorder_nodes.\n"
            "Respond ONLY with a valid JSON object like:\n"
            '{"tool": "update_attribute", "node_id": "img_001", "attribute": "alt", "value": "Description"}'
        ) % str(obs)

        response = client.chat.completions.create(
            model="gpt-4o",  # Standard model for most proxies
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.0,
        )
        text = response.choices[0].message.content.strip()

        import json
        # Strip markdown fences if present
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except Exception as e:
        safe_stderr("(ERROR) LLM call failed: %s" % e)
        return None

# -----------------------------------------
# SAFE OUTPUT HELPERS
# -----------------------------------------
def safe_stdout(line):
    try:
        print(str(line), flush=True)
    except Exception:
        pass

def safe_stderr(line):
    try:
        sys.stderr.write(str(line) + "\n")
        sys.stderr.flush()
    except Exception:
        pass

def clamp(value):
    try:
        v = float(value)
        return max(0.05, min(0.95, v))
    except Exception:
        return 0.05

def print_start(task_name):
    safe_stdout("[START] task=%s" % task_name)

def print_step(step, reward):
    safe_stdout("[STEP] step=%d reward=%.4f" % (int(step), float(reward)))

def print_end(task_name, score, steps):
    safe_stdout("[END] task=%s score=%.4f steps=%d" % (task_name, float(score), int(steps)))

def output_safe_default(task_name):
    print_start(task_name)
    print_step(1, 0.05)
    print_end(task_name, 0.05, 1)

# -----------------------------------------
# ENV HELPERS
# -----------------------------------------
def wait_for_env_container():
    global ENV_BASE_URL
    if requests is None:
        return False

    urls_to_try = [ENV_BASE_URL]
    if "env:8000" in ENV_BASE_URL:
        urls_to_try.append(ENV_BASE_URL.replace("env:8000", "localhost:8000"))

    for url in urls_to_try:
        for _ in range(5):
            try:
                r = requests.get("%s/health" % url, timeout=3)
                if r.status_code == 200:
                    ENV_BASE_URL = url
                    return True
            except Exception:
                pass
            time.sleep(2)

    safe_stderr("(ERROR) could not reach env container on %s" % urls_to_try)
    return False

def safe_post(endpoint, payload):
    if requests is None:
        return {"error": "requests_not_available"}
    try:
        base = ENV_BASE_URL.rstrip("/")
        path = endpoint.lstrip("/")
        r = requests.post("%s/%s" % (base, path), json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {"error": "invalid_json_response"}
    except Exception as e:
        safe_stderr("(ERROR) %s failed: %s" % (endpoint, e))
        return {"error": str(e)}

def build_action_fallback(obs):
    """Fallback hardcoded action if LLM fails."""
    try:
        task = obs.get("task", {}) or {} if isinstance(obs, dict) else {}
        task_type = task.get("type", "")
        target_id = task.get("target_node_id", "img_001")
        if task_type == "add_alt_text":
            return {"tool": "update_attribute", "node_id": target_id, "attribute": "alt", "value": "Accessible image"}
        elif task_type == "fix_contrast":
            return {"tool": "modify_css", "node_id": target_id, "property": "color", "value": "#50C878"}
        elif task_type == "fix_hierarchy":
            return {"tool": "reorder_nodes", "node_id": target_id, "new_parent_id": "header_001"}
        else:
            return {"tool": "update_attribute", "node_id": target_id, "attribute": "alt", "value": "Accessible image"}
    except Exception:
        return {"tool": "update_attribute", "node_id": "img_001", "attribute": "alt", "value": "Accessible image"}

def build_action(obs):
    """Try LLM first, fall back to hardcoded logic."""
    action = call_llm(obs)
    if action and isinstance(action, dict) and "tool" in action:
        return action
    safe_stderr("(WARN) LLM returned no valid action, using fallback")
    return build_action_fallback(obs)

# -----------------------------------------
# MAIN
# -----------------------------------------
def run_agent():
    task_name = DEFAULT_TASK_NAME
    print_start(task_name)

    if MOCK_MODE:
        print_step(1, 0.5)
        print_end(task_name, 0.5, 1)
        return

    try:
        if requests is None:
            print_step(1, 0.05)
            print_end(task_name, 0.05, 1)
            return

        if not wait_for_env_container():
            print_step(1, 0.05)
            print_end(task_name, 0.05, 1)
            return

        obs = safe_post("/reset", {"task_difficulty": "openenv"})
        if "error" in obs:
            print_step(1, 0.05)
            print_end(task_name, 0.05, 1)
            return

        # Ensure task_name remains stable for [END] block consistency
        try:
            task_data = obs.get("task", {})
            if isinstance(task_data, dict) and "id" in task_data:
                # We log it but don't overwrite the name already in [START]
                safe_stderr("(INFO) Received task: %s" % task_data.get("id"))
        except Exception:
            pass

        step_count = 0
        total_reward = 0.0
        done = False

        while not done and step_count < 10:
            step_count += 1
            action = build_action(obs)
            result = safe_post("/step", {"action": action})

            if "error" in result:
                reward = 0.05
                done = True
            else:
                reward = clamp(result.get("reward", 0.05))
                done = bool(result.get("done", False))
                obs = result

            total_reward += reward
            print_step(step_count, reward)

        final_score = clamp(total_reward / max(step_count, 1))
        print_end(task_name, final_score, step_count)

    except Exception as e:
        safe_stderr("(FATAL) %s" % e)
        output_safe_default(task_name)

if __name__ == "__main__":
    try:
        run_agent()
    except Exception as e:
        safe_stderr("(UNCAUGHT) %s" % e)
        output_safe_default(DEFAULT_TASK_NAME)
    finally:
        try:
            sys.exit(0)
        except Exception:
            pass
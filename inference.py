import os
import json
from openai import OpenAI
from env import UIAuditorEnv, Action

# ============================================================================
# Inference Baseline — Automated Web UI & Accessibility Auditor
# Scalar x Meta & Hugging Face Agentic AI Hackathon
# ============================================================================

# --- Required environment variables (per OpenEnv spec) ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "google/gemma-2-9b-it")
HF_TOKEN     = os.getenv("HF_TOKEN")          # NO default — must be supplied at runtime

# Optional — only required when using from_docker_image()
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")


def run_task(task_difficulty: str):
    # ── START log (required structured format) ──────────────────────────────
    print(f"[START] task={task_difficulty.upper()} model={MODEL_NAME} endpoint={API_BASE_URL}")

    env = UIAuditorEnv(task_difficulty=task_difficulty)
    obs = env.reset()

    system_prompt = (
        "You are an Expert Frontend UI/UX and Accessibility Auditor agent operating "
        "within a strictly typed OpenEnv environment.\n"
        "You have access to an Action space with 'update_attribute', 'modify_css', and "
        "'reorder_nodes'. Analyze the pure dictionary DOM meticulously. "
        "Target the specific 'node_id' described, resolving the accessibility or UI flaws "
        "to score a dense reward of 1.0. Do not hallucinate DOM attributes or IDs."
    )

    while not obs.is_done:
        step_num = env.steps + 1

        schema = Action.model_json_schema()
        user_content = (
            f"Current DOM State:\n{json.dumps(obs.dom_state, indent=2)}\n\n"
            f"Task: {obs.task_description}\n"
            "Please output the exact structured action needed to repair this DOM.\n\n"
            f"Your response must be ONLY a valid JSON object matching this schema:\n{json.dumps(schema, indent=2)}"
        )

        try:
            client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": system_prompt + "\nRespond with ONLY valid JSON.\n\n" + user_content}
                ]
            )

            raw_content = response.choices[0].message.content.strip()
            # Robust JSON extraction — handles markdown code fences from some models
            start_idx = raw_content.find('{')
            end_idx   = raw_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                raw_content = raw_content[start_idx:end_idx + 1]

            action = Action.model_validate_json(raw_content)

            obs, reward = env.step(action)

            # ── STEP log (required structured format) ───────────────────────
            print(
                f"[STEP] step={step_num} action={action.action_type} "
                f"node={action.node_id} score={reward.score}"
            )

        except Exception as e:
            # ── STEP log on error ────────────────────────────────────────────
            print(f"[STEP] step={step_num} error={str(e)}")
            break

    # ── END log (required structured format) ────────────────────────────────
    print(f"[END] task={task_difficulty.upper()} final_score={obs.current_score}")


if __name__ == "__main__":
    print(f"[START] Automated Web UI & Accessibility Auditor — Baseline Agent")
    print(f"[START] model={MODEL_NAME} endpoint={API_BASE_URL}")

    for level in ["easy", "medium", "hard"]:
        run_task(level)

    print("[END] All tasks completed.")

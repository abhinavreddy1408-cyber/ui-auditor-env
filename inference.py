import os
import json
from openai import OpenAI
from env import UIAuditorEnv, Action

# ============================================================================
# Step 3: Testing (Inference Baseline)
# Run an OpenAI-compatible agent against the OpenEnv Automated Web UI Auditor
# ============================================================================

# Environment variables setup (as defined in specs)
API_BASE_URL = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-2-9b-it")# Prioritize HF_TOKEN as per prompt instructions, fallback to OPENAI_API_KEY
API_KEY_STRING = os.getenv("HF_TOKEN", os.getenv("OPENAI_API_KEY", "your-api-key-here"))

# Support multiple API keys separated by comma for fallback resilience
API_KEYS = [k.strip() for k in API_KEY_STRING.split(",") if k.strip()]
if not API_KEYS:
    API_KEYS = ["your-api-key-here"]

def run_task(task_difficulty: str):
    print(f"\n{'='*60}")
    print(f"🚀 Starting Baseline Agent for Task: {task_difficulty.upper()}")
    print(f"{'='*60}")
    
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
        print(f"\n[Step {env.steps + 1}/15] 🎯 Score: {obs.current_score}")
        print(f"Feedback: {obs.feedback}")
        print(f"Task Instruction: {obs.task_description}")

        schema = Action.model_json_schema()
        user_content = (
            f"Current DOM State:\n{json.dumps(obs.dom_state, indent=2)}\n\n"
            f"Task: {obs.task_description}\n"
            "Please output the exact structured action needed to repair this DOM.\n\n"
            f"Your response must be ONLY a valid JSON object matching this schema:\n{json.dumps(schema, indent=2)}"
        )

        try:
            response = None
            last_error = None
            
            # Iterate through available keys and execute fallback if one fails
            for api_key in API_KEYS:
                client = OpenAI(base_url=API_BASE_URL, api_key=api_key)
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "user", "content": system_prompt + "\nRespond with ONLY valid JSON.\n\n" + user_content}
                        ]
                    )
                    break # Success! Break out of the fallback loop
                except Exception as e:
                    last_error = e
                    continue # Try the next key
                    
            if response is None:
                raise Exception(f"All {len(API_KEYS)} API keys failed. Last error: {last_error}")
            
            raw_content = response.choices[0].message.content.strip()
            # Robust JSON extraction to prevent 'trailing characters' decoding errors common with Gemma models
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                raw_content = raw_content[start_idx:end_idx+1]
            
            action = Action.model_validate_json(raw_content)
            
            # Readability logs
            print(f"\n🤖 Agent Output >> Action: {action.action_type} on '{action.node_id}'")
            if action.action_type == "update_attribute":
                print(f"   Update -> {action.attr_name}: '{action.new_value}'")
            elif action.action_type == "modify_css":
                print(f"   Style -> {action.css_property}: '{action.new_hex_code}'")
            elif action.action_type == "reorder_nodes":
                print(f"   Order -> {action.new_child_order}")
                
            obs, reward = env.step(action)
            print(f"🌍 Environment Evaluated >> Dense Result: {reward.score}")
            
        except Exception as e:
            print(f"\n❌ Error calling LLM API or structuring response: {e}")
            print("Ensure `openai >= 1.40.0` is installed and the API url/token are correct.")
            break

    print(f"\n🏁 Task {task_difficulty.upper()} Completed | Final Dense Score: {obs.current_score}/1.0")

if __name__ == "__main__":
    print("============================================================================")
    print("🔍 Automated Web UI & Accessibility Auditor (Baseline Agent Testing)")
    print(f"⚙️ Target Model: {MODEL_NAME}")
    print(f"🔗 Target Endpoint: {API_BASE_URL}")
    print("============================================================================")
    
    for level in ["easy", "medium", "hard"]:
        run_task(level)

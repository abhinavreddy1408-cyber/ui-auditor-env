import json
import os

from openai import OpenAI

from env import Action, UIAuditorEnv


API_BASE_URL = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemma-2-9b-it")
API_KEY = (
    os.getenv("OPENAI_API_KEY")
    or os.getenv("HF_TOKEN")
    or os.getenv("NVIDIA_API_KEY")
)

LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")


def run_task(task_difficulty: str) -> None:
    print(
        f"[START] task={task_difficulty.upper()} "
        f"model={MODEL_NAME} endpoint={API_BASE_URL}"
    )

    env = UIAuditorEnv(task_difficulty=task_difficulty)
    obs = env.reset(task_difficulty=task_difficulty)

    system_prompt = (
        "You are an Expert Frontend UI/UX and Accessibility Auditor agent operating "
        "within a strictly typed OpenEnv environment.\n"
        "You have access to an Action space with 'update_attribute', 'modify_css', "
        "and 'reorder_nodes'. Analyze the pure dictionary DOM meticulously. "
        "Target the specific 'node_id' described, resolving the accessibility or "
        "UI flaws to score a dense reward of 1.0. Do not hallucinate DOM "
        "attributes or IDs."
    )

    while not obs.done:
        step_num = env.steps + 1
        schema = Action.model_json_schema()
        user_content = (
            f"Current DOM State:\n{json.dumps(obs.dom_state, indent=2)}\n\n"
            f"Task: {obs.task_description}\n"
            "Please output the exact structured action needed to repair this DOM.\n\n"
            "Your response must be ONLY a valid JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )

        try:
            if not API_KEY:
                raise RuntimeError(
                    "Missing API key. Set OPENAI_API_KEY, HF_TOKEN, or NVIDIA_API_KEY."
                )

            client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            system_prompt
                            + "\nRespond with ONLY valid JSON.\n\n"
                            + user_content
                        ),
                    }
                ],
            )

            raw_content = response.choices[0].message.content.strip()
            start_idx = raw_content.find("{")
            end_idx = raw_content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                raw_content = raw_content[start_idx : end_idx + 1]

            action = Action.model_validate_json(raw_content)
            obs = env.step(action)

            print(
                f"[STEP] step={step_num} action={action.action_type} "
                f"node={action.node_id} score={obs.current_score}"
            )
        except Exception as exc:
            print(f"[STEP] step={step_num} error={str(exc)}")
            break

    print(f"[END] task={task_difficulty.upper()} final_score={obs.current_score}")


if __name__ == "__main__":
    print("[START] Automated Web UI & Accessibility Auditor - Baseline Agent")
    print(f"[START] model={MODEL_NAME} endpoint={API_BASE_URL}")

    for level in ["easy", "medium", "hard"]:
        run_task(level)

    print("[END] All tasks completed.")

import os
import random
import uvicorn
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from env import UIAuditorEnv, Action

app = FastAPI(title="ui-auditor-env", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

import graders

# ------------------------------------------------------------------
# TASK REGISTRY — IDs match openenv.yaml exactly
# ------------------------------------------------------------------
TASKS = {
    "easy": {
        "id": "easy",
        "type": "add_alt_text",
        "description": "Add descriptive alt text to hero image",
        "difficulty": "easy",
        "target_node_id": "img_001",
        "wcag_criterion": "1.1.1",
        "grader": graders.alt_text_grader,
    },
    "medium": {
        "id": "medium",
        "type": "fix_contrast",
        "description": "Fix CTA button color contrast to WCAG standards using #50C878",
        "difficulty": "medium",
        "target_node_id": "btn_001",
        "wcag_criterion": "1.4.3",
        "grader": graders.contrast_grader,
    },
    "hard": {
        "id": "hard",
        "type": "fix_hierarchy",
        "description": "Reorder and fix semantic header structure (H1 > H2 > H3)",
        "difficulty": "hard",
        "target_node_id": "h3_001",
        "wcag_criterion": "1.3.1",
        "grader": graders.hierarchy_grader,
    },
    "extra": {
        "id": "extra",
        "type": "add_labels",
        "description": "Add accessibility labels or aria-label to form inputs",
        "difficulty": "hard",
        "target_node_id": "input_001",
        "wcag_criterion": "1.3.1",
        "grader": graders.label_grader,
    },
}


# Module-level state
current_task_id: str = "easy"
env_instance = UIAuditorEnv()

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def to_openenv_dom(node_dict: dict) -> dict:
    return {
        "tag": node_dict.get("type", "div"),
        "id": node_dict.get("id", "unknown"),
        "attributes": {k: v for k, v in node_dict.items() if k not in ["type", "id", "children"]},
        "children": [to_openenv_dom(c) for c in node_dict.get("children", [])]
    }

def task_info(task_id: str) -> dict:
    """Return task dict without the grader function (safe to serialize)."""
    return {k: v for k, v in TASKS[task_id].items() if k != "grader"}

# ------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/validate")
@app.post("/validate")
def validate():
    return {
        "valid": True,
        "version": "1.0.0",
        "env_name": "ui-accessibility-auditor",
        "supported_actions": ["update_attribute", "modify_css", "reorder_nodes"],
        "tasks": [task_info(tid) for tid in TASKS],
    }

@app.post("/reset")
@app.post("/api/reset")
async def reset(request: Request):
    global current_task_id, env_instance

    try:
        body = await request.json()
    except Exception:
        body = {}

    difficulty = body.get("task_difficulty", "openenv")

    # Allow caller to pin a task, otherwise pick randomly so all 3 graders get exercised
    task_id = body.get("task_id")
    if task_id not in TASKS:
        task_id = random.choice(list(TASKS.keys()))
    current_task_id = task_id

    # Reset environment with task-specific difficulty and grader
    task = TASKS[current_task_id]
    obs = env_instance.reset(task_difficulty=task["difficulty"], grader=task["grader"])

    return {
        "observation": {"dom": to_openenv_dom(env_instance.dom)},
        "task": task_info(current_task_id),
        "reward": obs.current_score,
        "done": obs.done,
        "info": {
            "steps": env_instance.steps,
            "task_id": current_task_id,
        },
    }

@app.post("/step")
@app.post("/api/step")
async def step(request: Request):
    global current_task_id

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        action_raw = body.get("action", {})
        action_typed = Action(
            action_type=action_raw.get("tool") or action_raw.get("action_type") or "update_attribute",
            node_id=action_raw.get("node_id", "img_001"),
            attribute=action_raw.get("attribute") or action_raw.get("attr_name"),
            property=action_raw.get("property") or action_raw.get("css_property"),
            value=action_raw.get("value") or action_raw.get("new_value"),
            new_parent_id=action_raw.get("new_parent_id"),
            new_child_order=action_raw.get("new_child_order"),
        )
        obs = env_instance.step(action_typed)

        return {
            "observation": {"dom": to_openenv_dom(env_instance.dom)},
            "reward": obs.current_score,
            "done": obs.done or obs.current_score >= 0.8,
            "info": {
                "steps": env_instance.steps,
                "task_id": current_task_id,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------
def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
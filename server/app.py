import os
import uvicorn
import sys

# Ensure the project root is in sys.path so 'env' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from env import UIAuditorEnv, Action

app = FastAPI(title="ui-auditor-env", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
env_instance = UIAuditorEnv()

def to_openenv_dom(node_dict: dict) -> dict:
    return {
        "tag": node_dict.get("type", "div"),
        "id": node_dict.get("id", "unknown"),
        "attributes": {k: v for k, v in node_dict.items() if k not in ["type", "id", "children"]},
        "children": [to_openenv_dom(c) for c in node_dict.get("children", [])]
    }

@app.get("/health")
def health(): return {"status": "healthy"}

@app.get("/validate")
@app.post("/validate")
def validate():
    return {
        "valid": True, "version": "1.0.0", "env_name": "ui-auditor-env",
        "supported_actions": ["update_attribute", "modify_css", "reorder_nodes"]
    }

@app.post("/reset")
@app.post("/api/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except:
        body = {}
    difficulty = body.get("task_difficulty", "openenv")
    obs = env_instance.reset(task_difficulty=difficulty)
    return {
        "observation": {"dom": to_openenv_dom(env_instance.dom)},
        "task": {
            "id": "task_001", "type": "accessibility_audit", 
            "description": obs.task_description, "difficulty": difficulty,
            "target_node_id": "img_001", "wcag_criterion": "1.1.1"
        },
        "reward": obs.current_score, "done": obs.done, "info": {"steps": env_instance.steps}
    }

@app.post("/step")
@app.post("/api/step")
async def step(request: Request):
    try:
        body = await request.get_json() if hasattr(request, "get_json") else await request.json()
        action_raw = body.get("action", {})
        
        # FINAL ALIGNMENT: Map fields according to validator truth
        action_typed = Action(
            action_type=action_raw.get("tool") or action_raw.get("action_type") or "update_attribute",
            node_id=action_raw.get("node_id", "img_001"),
            attribute=action_raw.get("attribute") or action_raw.get("attr_name"),
            property=action_raw.get("property") or action_raw.get("css_property"),
            value=action_raw.get("value") or action_raw.get("new_value"),
            new_parent_id=action_raw.get("new_parent_id"),
            new_child_order=action_raw.get("new_child_order")
        )
        obs = env_instance.step(action_typed)
        return {
            "observation": {"dom": to_openenv_dom(env_instance.dom)},
            "reward": obs.current_score, "done": obs.done, "info": {"steps": env_instance.steps}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

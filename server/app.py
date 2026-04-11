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

# ---------------------------------------------------------------------------
# OpenEnv Standard Pydantic v2 Models
# ---------------------------------------------------------------------------

class DOMNode(BaseModel):
    tag: str
    id: str
    attributes: dict = Field(default_factory=dict)
    children: list = Field(default_factory=list)

class TaskInfo(BaseModel):
    id: str
    type: str
    description: str
    difficulty: str
    target_node_id: Optional[str] = None
    wcag_criterion: Optional[str] = None

class ResetResponse(BaseModel):
    observation: Dict[str, Any]
    task: TaskInfo
    reward: float = 0.0
    done: bool = False
    info: Dict[str, Any]

# ---------------------------------------------------------------------------
# FastAPI initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Automated Web UI & Accessibility Auditor",
    description="Scalar Hackathon - OpenEnv Compliant AI Agent Environment",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance
env_instance = UIAuditorEnv()

# ---------------------------------------------------------------------------
# Helper: DOM Mapper (Internal Dict -> OpenEnv DOMNode)
# ---------------------------------------------------------------------------
def to_openenv_dom(node_dict: dict) -> dict:
    """Recursively transforms internal DOM structure to OpenEnv standard."""
    return {
        "tag": node_dict.get("type", "div"),
        "id": node_dict.get("id", "unknown"),
        "attributes": {k: v for k, v in node_dict.items() if k not in ["type", "id", "children"]},
        "children": [to_openenv_dom(c) for c in node_dict.get("children", [])]
    }

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Mandatory health check."""
    return {"status": "healthy"}

@app.get("/render")
def render_dom():
    """Expose the current visual state for debugging."""
    return {"dom": env_instance.dom}

@app.post("/validate")
def validate_env():
    """OpenEnv standard validation endpoint."""
    return {
        "valid": True,
        "version": "1.0.0",
        "env_name": "ui-auditor-env",
        "supported_actions": [
            "update_attribute",
            "modify_css",
            "reorder_nodes"
        ]
    }

@app.post("/reset")
@app.post("/api/reset")
async def reset_handler(request: Request):
    """
    OpenEnv standard reset. 
    Accepts empty {} or custom task difficulty.
    """
    try:
        # Handle empty body gracefully
        body = {}
        try:
            body = await request.json()
        except:
            pass
            
        difficulty = body.get("task_difficulty", "openenv")
        obs_internal = env_instance.reset(task_difficulty=difficulty)
        
        # Build OpenEnv response
        return {
            "observation": {
                "dom": to_openenv_dom(env_instance.dom)
            },
            "task": {
                "id": f"task_{difficulty}",
                "type": "accessibility_audit",
                "description": obs_internal.task_description,
                "difficulty": difficulty,
                "target_node_id": "img_001",
                "wcag_criterion": "1.1.1"
            },
            "reward": 0.05, 
            "done": False,
            "info": {
                "episode": 1,
                "max_steps": 15,
                "current_step": 0,
                "feedback": "Environment reset. Ready for audit."
            }
        }
    except Exception as e:
        print(f"Reset Error: {e}", file=sys.stderr)
        return {
            "observation": {"dom": {"tag": "div", "id": "root", "attributes": {}, "children": []}},
            "task": {"id": "error", "type": "error", "description": str(e), "difficulty": "easy"},
            "reward": 0.0,
            "done": True,
            "info": {"error": True}
        }

@app.post("/step")
@app.post("/api/step")
async def step_handler(req: Request):
    """
    OpenEnv standard step. 
    Accepts action and returns nested rewards.
    """
    try:
        body = await req.json()
        action_raw = body.get("action", {})
        
        # Pydantic Action expects action_type, not tool
        action_typed = Action(
            action_type=action_raw.get("tool") or action_raw.get("action_type") or "update_attribute",
            node_id=action_raw.get("node_id", "img_001"),
            attr_name=action_raw.get("attribute") or action_raw.get("attr_name"),
            new_value=action_raw.get("value") or action_raw.get("new_value"),
            css_property=action_raw.get("css_property"),
            new_hex_code=action_raw.get("new_hex_code"),
            new_child_order=action_raw.get("new_child_order")
        )

        obs_internal = env_instance.step(action_typed)
        
        return {
            "observation": {
                "dom": to_openenv_dom(env_instance.dom)
            },
            "reward": obs_internal.current_score,
            "done": obs_internal.done,
            "info": {
                "current_step": env_instance.steps,
                "feedback": obs_internal.feedback
            }
        }
    except Exception as e:
        print(f"Step Error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))

def main() -> None:
    # Internal API typically runs on port 8000
    port = int(os.getenv("PORT", "8000"))
    # Scalar/OpenEnv requires 0.0.0.0
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

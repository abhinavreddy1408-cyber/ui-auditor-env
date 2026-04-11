import json
import os
import sys
from pathlib import Path
from typing import List, Optional

# Ensure the root directory is in the path so we can import env.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from openenv.core.env_server.http_server import create_app
from pydantic import BaseModel

from env import Action, Observation, UIAuditorEnv


class ResetRequest(BaseModel):
    task_difficulty: Optional[str] = "easy"


class StepRequest(BaseModel):
    action: Action
    task_difficulty: Optional[str] = None


class RunAgentRequest(BaseModel):
    task_difficulty: str = "easy"
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_steps: int = 8


class RunAgentResponse(BaseModel):
    final_score: float
    steps: List[dict]


app = create_app(
    UIAuditorEnv,
    Action,
    Observation,
    env_name="ui-accessibility-auditor",
    max_concurrent_envs=1,
)

# ---------------------------------------------------------------------------
# Cross-origin + SPA static hosting
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST_PATH = Path(__file__).resolve().parent.parent / "web" / "dist"
INDEX_FILE = DIST_PATH / "index.html"

if DIST_PATH.exists():
    app.mount("/ui", StaticFiles(directory=DIST_PATH, html=True), name="ui")


# ---------------------------------------------------------------------------
# Simple health check
# ---------------------------------------------------------------------------
@app.get("/")
def health_check():
    """Root health check to ensure the space is alive."""
    return {"status": "ok", "env": "ui-accessibility-auditor"}


# Helper to expose namespaced routes at the root level for simpler validators
@app.post("/reset")
async def root_reset():
    return RedirectResponse(url="/envs/ui-accessibility-auditor/reset", status_code=307)


@app.post("/step")
async def root_step():
    return RedirectResponse(url="/envs/ui-accessibility-auditor/step", status_code=307)


@app.get("/metadata")
async def root_metadata():
    return RedirectResponse(url="/envs/ui-accessibility-auditor/metadata", status_code=307)


# ---------------------------------------------------------------------------
# UI Playground endpoints
# ---------------------------------------------------------------------------
ui_env = UIAuditorEnv(task_difficulty="easy")
last_observation: Optional[Observation] = ui_env.reset(task_difficulty="easy")


@app.get("/api/tasks")
@app.get("/ui/tasks")
async def list_tasks():
    return {
        "tasks": [
            {
                "id": "easy",
                "label": "Easy – Hero Alt Text",
                "description": "Add descriptive alt text to hero image",
            },
            {
                "id": "medium",
                "label": "Medium – Button Contrast",
                "description": "Fix CTA button color contrast to WCAG using #50C878",
            },
            {
                "id": "hard",
                "label": "Hard – Semantic Header",
                "description": "Reorder and fix semantic header structure (H1 > H2 > H3)",
            },
        ]
    }


@app.get("/health")
async def health_check_internal():
    """
    Required for Docker healthcheck.
    Without this, inference.py cannot verify the env is ready.
    """
    return {"status": "healthy", "service": "web-auditor-api"}


@app.post("/api/reset")
@app.post("/ui/reset")
async def ui_reset(payload: ResetRequest):
    global last_observation
    task = payload.task_difficulty or "easy"
    last_observation = ui_env.reset(task_difficulty=task)
    return last_observation


@app.post("/api/step")
@app.post("/ui/step")
async def ui_step(payload: StepRequest):
    global last_observation
    task = payload.task_difficulty
    obs = ui_env.step(payload.action, task_difficulty=task)
    last_observation = obs
    return obs


@app.get("/api/state")
@app.get("/ui/state")
async def ui_state():
    return last_observation or ui_env.reset(task_difficulty="easy")


@app.post("/api/run-agent", response_model=RunAgentResponse)
@app.post("/ui/run-agent", response_model=RunAgentResponse)
async def ui_run_agent(payload: RunAgentRequest):
    # Validators require all LLM traffic to go through the injected LiteLLM proxy.
    try:
        base_url = os.environ["API_BASE_URL"]
        api_key = os.environ["API_KEY"]
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required environment variable: {e.args[0]}. This is required for the LiteLLM proxy.",
        )

    model = payload.model

    env = UIAuditorEnv(task_difficulty=payload.task_difficulty)
    obs = env.reset(task_difficulty=payload.task_difficulty)
    steps: List[dict] = []

    system_prompt = (
        "You are an Expert Frontend UI/UX and Accessibility Auditor agent operating "
        "within a strictly typed OpenEnv environment.\n"
        "You have access to an Action space with 'update_attribute', 'modify_css', "
        "and 'reorder_nodes'. Analyze the pure dictionary DOM meticulously. "
        "Target the specific 'node_id' described, resolving the accessibility or "
        "UI flaws to score a dense reward of 1.0. Do not hallucinate DOM "
        "attributes or IDs."
    )

    client = OpenAI(base_url=base_url, api_key=api_key)

    while not obs.done and len(steps) < max(1, payload.max_steps):
        schema = Action.model_json_schema()
        user_content = (
            f"Current DOM State:\\n{json.dumps(obs.dom_state, indent=2)}\\n\\n"
            f"Task: {obs.task_description}\\n"
            "Please output the exact structured action needed to repair this DOM.\\n\\n"
            "Your response must be ONLY a valid JSON object matching this schema:\\n"
            f"{json.dumps(schema, indent=2)}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": system_prompt + "\\nRespond with ONLY valid JSON.\\n\\n" + user_content,
                }
            ],
        )

        raw_content = (response.choices[0].message.content or "").strip()
        start_idx = raw_content.find("{")
        end_idx = raw_content.rfind("}")
        if start_idx == -1 or end_idx == -1:
            raise HTTPException(
                status_code=500,
                detail=f"Model response not JSON: {raw_content}",
            )
        action = Action.model_validate_json(raw_content[start_idx : end_idx + 1])
        obs = env.step(action)
        steps.append(
            {
                "step": len(steps) + 1,
                "action": action.model_dump(),
                "score": obs.current_score,
                "feedback": obs.feedback,
            }
        )

    return RunAgentResponse(final_score=obs.current_score, steps=steps)


# Serve SPA index for deep links
if DIST_PATH.exists():
    @app.get("/ui/{full_path:path}")
    async def spa_index(full_path: str):
        del full_path
        return FileResponse(INDEX_FILE)


def main() -> None:
    # Internal API typically runs on port 8000
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

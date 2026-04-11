import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from env import UIAuditorEnv, Action

# ---------------------------------------------------------------------------
# FastAPI initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Automated Web UI & Accessibility Auditor",
    description="Scalar Hackathon - Zero-Browser AI Agent Environment",
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
# Request/Response Models
# ---------------------------------------------------------------------------
class StepRequest(BaseModel):
    action: Action
    task_difficulty: Optional[str] = "easy"

class ResetRequest(BaseModel):
    task_difficulty: Optional[str] = "easy"

# ---------------------------------------------------------------------------
# Simple health check
# ---------------------------------------------------------------------------
@app.get("/")
@app.get("/health")
def health_check():
    """Root health check to ensure the space is alive."""
    return {"status": "healthy", "env": "ui-accessibility-auditor"}

# ---------------------------------------------------------------------------
# Core API Routes
# ---------------------------------------------------------------------------
@app.post("/api/reset")
@app.post("/reset")
def reset_env(req: Optional[ResetRequest] = None):
    try:
        difficulty = req.task_difficulty if req else "easy"
        obs = env_instance.reset(task_difficulty=difficulty)
        return obs.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/step")
@app.post("/step")
def step_env(req: StepRequest):
    try:
        # Standardize difficulty before stepping
        if req.task_difficulty:
            env_instance.task_difficulty = req.task_difficulty.lower()
        
        obs = env_instance.step(req.action)
        return obs.dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    # Internal API typically runs on port 8000
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

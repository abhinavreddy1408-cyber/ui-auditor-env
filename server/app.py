import os
import sys

# Ensure the root directory is in the path so we can import env.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from openenv.core.env_server.http_server import create_app

from env import Action, Observation, UIAuditorEnv


app = create_app(
    UIAuditorEnv,
    Action,
    Observation,
    env_name="ui-accessibility-auditor",
    max_concurrent_envs=1,
)


@app.get("/")
def health_check():
    """Root health check to ensure the space is alive."""
    return {"status": "ok", "env": "ui-accessibility-auditor"}


# Helper to expose namespaced routes at the root level for simpler validators
@app.post("/reset")
async def root_reset():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/envs/ui-accessibility-auditor/reset", status_code=307)


@app.post("/step")
async def root_step():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/envs/ui-accessibility-auditor/step", status_code=307)


@app.get("/metadata")
async def root_metadata():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/envs/ui-accessibility-auditor/metadata", status_code=307)


def main() -> None:
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

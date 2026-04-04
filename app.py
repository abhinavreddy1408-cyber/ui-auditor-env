import os

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
async def root_reset(request: bytes = None):
    # Pass-through or redirect doesn't work well for POST with bytes,
    # but create_app usually puts the env router in app.router.
    # A cleaner way is to use the existing app's handler.
    from fastapi import Request
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/envs/ui-accessibility-auditor/reset")


@app.post("/step")
async def root_step():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/envs/ui-accessibility-auditor/step")


def main() -> None:
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

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


def main() -> None:
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

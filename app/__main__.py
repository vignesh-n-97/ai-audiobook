"""CLI entry point: python -m app"""

import uvicorn

from app.core.config import get_config

if __name__ == "__main__":
    cfg = get_config()
    uvicorn.run(
        "app.application:app",
        host=cfg.api_host,
        port=cfg.api_port,
        reload=cfg.api_debug,
    )

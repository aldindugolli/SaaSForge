#!/usr/bin/env python3
"""Application entry point."""
import os

env = os.environ.get("FLASK_ENV", "development")

if env == "development" and not os.environ.get("DATABASE_URL", "").startswith("postgres"):
    from app.core.local_config import LocalConfig
    from app import create_app
    app = create_app(LocalConfig)
else:
    from app import create_app
    app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)

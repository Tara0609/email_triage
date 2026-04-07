"""
Entry point for OpenEnv validator compatibility.
Imports the main FastAPI app from the root app module.
"""
import sys
import os

# Ensure the project root is on the path so 'env' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: F401  — re-export for uvicorn server.app:app


def main():
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()

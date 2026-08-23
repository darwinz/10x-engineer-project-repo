"""PromptLab API Server

Run with: python main.py   (from the backend/ directory)

The app is passed to uvicorn as an import string rather than an object:
uvicorn refuses to start with reload=True when given an object, because the
reloader has to re-import the application in a fresh process.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)

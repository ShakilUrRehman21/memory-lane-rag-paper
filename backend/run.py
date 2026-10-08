import uvicorn
import sys
import os
from pathlib import Path

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent))

def start():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() in ("true", "1")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    start()



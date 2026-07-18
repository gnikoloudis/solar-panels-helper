import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_PORT = 8002
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def main():
    os.chdir(ROOT)

    proc_backend = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "solarpanels.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        env={**os.environ, "PYTHONPATH": "src"},
        cwd=ROOT,
    )

    proc_frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "frontend",
        shell=True,
    )

    print(f"Backend running at http://127.0.0.1:{BACKEND_PORT}")
    print("Frontend dev server starting at http://localhost:5173")
    print("Press Ctrl+C to stop both.")

    try:
        proc_backend.wait()
        proc_frontend.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc_backend.terminate()
        proc_frontend.terminate()
        proc_backend.wait()
        proc_frontend.wait()


if __name__ == "__main__":
    main()

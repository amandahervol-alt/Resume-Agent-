"""
Resume Recommendation Agent — Standalone Server & CLI Launcher
----------------------------------------------------------------
Launches the FastAPI backend and serves the interactive recommendation portal.
"""

import sys
import argparse
import webbrowser
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))


def launch_server(port: int = 8000, open_browser: bool = True):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    import uvicorn
    from main import app

    print("\n" + "=" * 65)
    print("💼 RESUME SERVICE PACKAGE RECOMMENDATION AGENT")
    print("=" * 65)
    print(f"[*] Serving web interface at: http://localhost:{port}")
    print(f"[*] API Endpoint: http://localhost:{port}/chat")
    print("=" * 65)

    if open_browser:
        webbrowser.open(f"http://localhost:{port}")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="Resume Recommendation Agent Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-serve", action="store_true", help="Validate imports and exit without running server")

    args = parser.parse_args()

    # Validate imports
    from main import app  # noqa: F401
    import rules  # noqa: F401
    import extraction  # noqa: F401

    print("[OK] Backend successfully loaded (FastAPI + Rules Engine + Signal Extraction).")

    if not args.no_serve:
        launch_server(port=args.port, open_browser=True)


if __name__ == "__main__":
    main()

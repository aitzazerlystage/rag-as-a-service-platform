"""
Launch a bundled SPA if present; otherwise explain what is missing.

run_frontend.py adds this repo's `src` directory to sys.path and calls main().
"""

from __future__ import annotations

import os
import sys
import subprocess


def main() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for name in ("Frontend", "frontend", "web", "client"):
        app_dir = os.path.join(root, name)
        pkg = os.path.join(app_dir, "package.json")
        if os.path.isfile(pkg):
            print(f"Starting dev server from {app_dir}")
            os.chdir(app_dir)
            try:
                subprocess.run(["npm", "run", "dev"], check=False)
            except FileNotFoundError:
                print("npm not found on PATH; install Node.js or run the frontend manually.", file=sys.stderr)
                sys.exit(1)
            return

    print(
        "No frontend app in this repository: add a folder named frontend, web, or client "
        f"with package.json under {root}, then run run_frontend.py again.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()

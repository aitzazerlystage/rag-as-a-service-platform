"""
Thin entry point: keeps `app` in this module so `uvicorn app:app` and `python app.py` work.
Implementation lives in `main.py` and the `routers/` package.
"""

from main import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()

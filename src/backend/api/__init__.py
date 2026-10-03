

# Only expose submodules (routers), NOT the app
from backend.api import insert, query,generate_api_key

__all__ = ["insert", "query","generate_api_key"]

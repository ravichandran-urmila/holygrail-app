import sys, os

# Ensure the backend package directory is on the path so that
# `from app.main import app` resolves correctly from /var/task/backend/
_backend_dir = os.path.dirname(__file__)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.main import app  # noqa: E402  (FastAPI ASGI app)

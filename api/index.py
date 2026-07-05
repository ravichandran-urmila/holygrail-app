"""Vercel serverless entry point — exposes the FastAPI ASGI app.

Vercel's @vercel/python runtime detects the module-level `app` (an ASGI app)
and serves it. Routes are prefixed with /api (see vercel.json rewrite).
"""

import os
import sys

# Make the backend package importable from the repo root on Vercel.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402  (ASGI app served by Vercel)

__all__ = ["app"]

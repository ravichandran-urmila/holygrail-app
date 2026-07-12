FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy watchlist data (watchlist.py expects ../../watchlist.json relative to app/)
COPY watchlist.json ./watchlist.json

# Default port (Railway overrides via $PORT)
ENV PORT=8000
EXPOSE 8000

# Use shell form so $PORT gets expanded at runtime
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT

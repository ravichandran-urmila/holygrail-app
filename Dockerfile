FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for compiling python packages if any
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to cache package installs
COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Expose default Streamlit port (can be overridden by $PORT at runtime via run.sh)
EXPOSE 8501

# Mark startup script executable and set as entrypoint
RUN chmod +x run.sh
ENTRYPOINT ["./run.sh"]

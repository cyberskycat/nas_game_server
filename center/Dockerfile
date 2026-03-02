FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Center code
COPY center /app/center
# Copy Frontend build
COPY frontend/dist /app/frontend/dist

# Expose the API port
EXPOSE 8123

# Set host to 0.0.0.0 for external access in Docker
CMD ["uvicorn", "center.app.main:app", "--host", "0.0.0.0", "--port", "8123"]

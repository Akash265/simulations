# Use Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only copy the Distribution-Center directory (and other files you need)
COPY Distribution-Center /app/Distribution-Center

# Expose FastAPI port
EXPOSE 8000

# Set the working directory to the Distribution-Center folder
WORKDIR /app/Distribution-Center

# Start FastAPI application
CMD ["uvicorn", "app-celery:app", "--host", "0.0.0.0", "--port", "8000"]

# Python runtime for the AI microservice.
# ai-service/Dockerfile uses python:3.10-slim; local development may run a newer Python
# (3.11, 3.12, 3.13) — requirements.txt is compatible with both.
# The container image is pinned to 3.10 for reproducibility.
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask server
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
FROM python:3.11.9-slim

# Set environment variables to prevent Python from writing .pyc files and to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /sybilla

# Create a non-root user and group
RUN addgroup --system app && adduser --system --group app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code as the new user
COPY --chown=app:app app ./app
COPY --chown=app:app static ./static
COPY --chown=app:app templates ./templates
COPY --chown=app:app server.py .
COPY --chown=app:app models.py .
COPY --chown=app:app oracle_client.py .
COPY --chown=app:app start.sh .

# Make start script executable
RUN chmod +x ./start.sh

# Switch to the non-root user
USER app

EXPOSE 9090

CMD ["./start.sh"]

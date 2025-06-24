FROM python:3.11-slim

WORKDIR /sybilla

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY templates ./templates
COPY reports ./reports
COPY server.py .
COPY start.sh .

EXPOSE 9090

CMD ["./start.sh"]
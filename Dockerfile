FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install fastapi uvicorn

ENV PYTHONUNBUFFERED=1

CMD ["python3", "RaftNode.py"]
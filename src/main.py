from fastapi import FastAPI, Response, status, Request
import os
import random
from typing import List
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from otel.metrics import request_counter, active_users_gauge


APP_NAME = os.getenv("APP_NAME", "api-otel")

app = FastAPI(
    title="OTEL Example API",
    description="Simple API to test observability with OpenTelemetry",
    version="1.0.0",
)

# Rota raiz
@app.get("/")
async def read_root():
    request_counter.add(1, {"endpoint": "/", "app": APP_NAME, "method": "GET"})
    active_users_gauge.set(1, {"app": APP_NAME})
    return {"message": "Hello World"}

# Rota /users
@app.get("/users")
async def read_users():
    request_counter.add(1, {"endpoint": "/users", "app": APP_NAME, "method": "GET"})
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]
    return users

#Rota /process
@app.post("/process")
def process_request():
    request_counter.add(1, {"endpoint": "/process", "app": APP_NAME, "method": "POST"})
    return {"message": "Processing request..."}

# Rota /metrics
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


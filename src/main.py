from fastapi import FastAPI, Response, status, Request,  HTTPException
import os
import random
from pydantic import BaseModel
import time
import requests
from typing import List, Any, Dict, Optional
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from otel.metrics import request_counter, active_users_gauge, response_time_histogram
from otel.tracing import tracer, propagator
from otel.logs import logger
import config
from opentelemetry.propagate import inject, extract
from opentelemetry.semconv.attributes.server_attributes import (
    SERVER_ADDRESS,
    SERVER_PORT
)

from opentelemetry.semconv.attributes.service_attributes import (
    SERVICE_NAME,
    SERVICE_VERSION
)

APP_NAME = config.APP_NAME
TARGET_API_ENV = config.TARGET_API_ENV
APP_VERSION = config.APP_VERSION

app = FastAPI(
    title="OTEL Example API",
    description="Simple API to test observability with OpenTelemetry",
    version=APP_VERSION,
)

# Rota raiz
@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed",
                extra={
                    "endpoint": "/",
                    "app": APP_NAME,
                    "method": "GET"
                }
                )
    request_counter.add(1, {"endpoint": "/", "app": APP_NAME, "method": "GET"})
    active_users_gauge.set(1, {"app": APP_NAME})
    return {"message": f"Hello World!! From {APP_NAME}"}


#Rota /process
@app.post("/process-old")
def process_request(response: Response, request: Request):
    request_counter.add(1, {"endpoint": "/process", "app": APP_NAME, "method": "POST"})

    base_url = TARGET_API_ENV
    if not base_url:
        raise HTTPException(status_code=500, detail="Variável de ambiente TARGET_API_ENV não configurada")

    url = f"{base_url.rstrip('/')}/response_time"
    print(url)

    if APP_NAME == "app-c":
        return {"message": "Processing request... No downstream API to call."}

    context = propagator.extract(request.headers)
    with tracer.start_as_current_span("process_request", context=context) as span:
        span.set_attribute("downstream.url", url)
        span.set_attribute("http.method", "GET")
        if request and request.client:
            span.set_attribute("http.client_ip", request.client.host)

        # Simula pequeno processamento local
        time.sleep(random.uniform(0.1, 0.5))

        # Headers p/ propagação de trace e correlação
        headers = {}
        try:
            from opentelemetry.propagate import inject
            inject(headers)  # adiciona traceparent/tracestate se OTEL estiver ativo
        except Exception:
            pass

        req_id = request.headers.get("x-request-id")
        if req_id:
            headers["x-request-id"] = req_id

        # Repasse de query params do POST local para o GET downstream (opcional)
        params = request.query_params  # aceita Mapping; para chaves repetidas, também aceita lista de tuplas

        try:
            with requests.Session() as s:
                resp = s.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=(3, 10),  
                )
                span.set_attribute("downstream.status_code", resp.status_code)
                resp.raise_for_status()

        except requests.exceptions.HTTPError as e:
            span.record_exception(e)
            status = e.response.status_code if e.response is not None else 502
            text = (e.response.text if e.response is not None else str(e))[:300]
            raise HTTPException(status_code=status, detail=f"Erro da API downstream: {text}")

        except requests.exceptions.RequestException as e:
            span.record_exception(e)
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao chamar a API downstream: {e.__class__.__name__}: {str(e)}"
            )

    # Espelha o status 2xx da downstream
    response.status_code = resp.status_code

    # Tenta repassar um cabeçalho útil de correlação (opcional)
    tp = resp.headers.get("traceparent")
    if tp:
        response.headers["traceparent-downstream"] = tp

    # Corpo de retorno
    try:
        body = resp.json()
    except ValueError:
        body = resp.text

    return {"message": "Processing request...", "downstream": body}



def _downstream_url_from_env() -> Optional[str]:
    base = config.TARGET_API_ENV.strip()
    print(f'URL: {base}')
    if not base:
        return None
    base = base.rstrip("/")
    return base if base.endswith("/process") else f"{base}/process"

@app.post("/process")
def process_request(response: Response, request: Request):
    # métrica básica
    try:
        request_counter.add(1, {"endpoint": "/process", "app": APP_NAME, "method": "POST"})
    except Exception:
        pass

    downstream_url = _downstream_url_from_env()
    print(f'Downstream URL: {downstream_url}')

    # extrai contexto do caller p/ manter o trace
    context = extract(dict(request.headers))



    with tracer.start_as_current_span("process_request", context=context) as span:
        span.set_attribute("app.name", APP_NAME)
        span.set_attribute("http.method", "POST")
        span.set_attribute("SERVER_ADDRESS", request.client.host)
        span.set_attribute("SERVER_PORT", request.client.port)
        span.set_attribute("http.route", request.url.path)
        if request and request.client:
            span.set_attribute("http.client_ip", request.client.host)

        # simula trabalho local
        time.sleep(random.uniform(0.1, 0.5))
        span_context = span.get_span_context()
        log_context = {
            SERVICE_NAME: APP_NAME,
            SERVICE_VERSION: APP_VERSION,
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
        }

        logger.info("Processing request...", extra=log_context)

        # se não há downstream configurada → responde local
        if not downstream_url:
            span.set_attribute("downstream.invoked", False)
            response.status_code = 200
            return {"message": "Processed locally (no TARGET_API_ENV configured)."}

        # headers com propagação OTEL + correlação
        headers: Dict[str, str] = {}
        try:
            inject(headers)  # adiciona traceparent/tracestate
        except Exception:
            pass

        # repassa x-request-id (se houver)
        req_id = request.headers.get("x-request-id")
        if req_id:
            headers["x-request-id"] = req_id

        # repassar todos os query params recebidos para a downstream
        fwd_params = list(request.query_params.multi_items())

        span.set_attribute("downstream.url", downstream_url)
        span.set_attribute("downstream.method", "POST")

        try:
            with requests.Session() as s:
                # POST sem corpo; apenas headers e params
                resp = s.post(downstream_url, headers=headers, params=fwd_params, timeout=(3, 10))
                span.set_attribute("downstream.status_code", resp.status_code)
                resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            span.record_exception(e)
            status = e.response.status_code if e.response is not None else 502
            text = (e.response.text if e.response is not None else str(e))[:300]
            raise HTTPException(status_code=status, detail=f"Erro da API downstream: {text}")
        except requests.exceptions.RequestException as e:
            span.record_exception(e)
            raise HTTPException(status_code=502, detail=f"Falha ao chamar a API downstream: {e.__class__.__name__}: {str(e)}")

        # espelha status da downstream
        response.status_code = resp.status_code

        # repassa traceparent da downstream (útil p/ correlação)
        tp = resp.headers.get("traceparent")
        if tp:
            response.headers["traceparent-downstream"] = tp

        # corpo de retorno (se houver)
        try:
            downstream_body = resp.json()
        except ValueError:
            downstream_body = resp.text

        return {
            "message": "Processing request... (downstream invoked)",
            "called": downstream_url,
            "downstream": downstream_body,
        }
    
@app.get("/response_time")
def get_response_time():
    """
    Endpoint para simular latência 
    """
    start_time = time.time()
    time.sleep(random.uniform(0.10, 0.50))
    duration = time.time() - start_time
    response_time_histogram.record(duration * 1000, {"app": APP_NAME, "endpoint": "/response_time", "method": "GET"})
    return {"response_time": duration * 1000}



# Rota /metrics
@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


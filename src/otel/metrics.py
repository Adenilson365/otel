from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
import os
from typing import Iterable
from opentelemetry.metrics import CallbackOptions, Observation
import random
import psutil

APP_NAME = os.getenv("APP_NAME", "api-otel")

prometheus_reader = PrometheusMetricReader()

#Define o provider de métricas
metrics.set_meter_provider(
    MeterProvider(
        metric_readers=[prometheus_reader]
    )
)

meter = metrics.get_meter(__name__)

# Cria um contador de requisições
request_counter = meter.create_counter(
    name="app_request_total",
    description="Counts the number of requests by endpoint",
    unit="1",
)

def get_random_value(options: CallbackOptions) -> Iterable[Observation]:
    return [Observation(random.randint(1, 100), {"app": APP_NAME})]


random_counter = meter.create_observable_counter(
    name="random_value",
    callbacks=[get_random_value],
    description="Generates a random value between 1 and 100",
)

###### GAUGES ######

active_users_gauge = meter.create_gauge(
    name="active_users",
    description="Tracks the number of active users",
    unit="1",
)

process = psutil.Process()

def get_memory_usage(options: CallbackOptions) -> Iterable[Observation]:
    mem_info = process.memory_info()
    return [Observation(mem_info.rss, {"app": APP_NAME})]


memory_usage_gauge = meter.create_observable_gauge(
    name="memory_usage_bytes",
    callbacks=[get_memory_usage],
    description="Tracks the memory usage of the application in bytes",
)

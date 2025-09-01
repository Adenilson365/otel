
from typing import Iterable
import random
import psutil
import config
#Bibliotecas de observabilidade
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader 



APP_NAME = config.APP_NAME

prometheus_reader = PrometheusMetricReader()
otlp_metric_exporter = OTLPMetricExporter(
    endpoint=f'{config.OTLP_ENDPOINT}/v1/metrics'
)

otlp_metric_reader = PeriodicExportingMetricReader(
    otlp_metric_exporter, 
    export_interval_millis=1000)
#Define o provider de métricas
metrics.set_meter_provider(
    MeterProvider(
        metric_readers=[prometheus_reader, otlp_metric_reader]
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

response_time_histogram = meter.create_histogram(
    name="response_time_ms",
    description="Tracks the response time of requests",
    unit="ms",
    explicit_bucket_boundaries_advisory=[0, 50, 100, 200, 300, 400]
)

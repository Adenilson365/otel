import os
import config
# Bibliotecas de rastreamento
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import (
    # Armazena em lotes e envia para o exporter de forma agrupada
    BatchSpanProcessor,
    # Exporta para o console
    ConsoleSpanExporter
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.semconv.attributes.service_attributes import (
    # Usando dessa forma os serviços vão seguir o padrão de nomenclatura do OpenTelemetry
    SERVICE_NAME,
    SERVICE_VERSION
)


APP_NAME = config.APP_NAME
OTLP_ENDPOINT = f'{config.OTLP_ENDPOINT}/v1/traces'

resource = Resource.create({
    SERVICE_NAME: config.APP_NAME,
    SERVICE_VERSION: config.APP_VERSION
})

provider = TracerProvider(resource=resource)
processor_console = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor_console)
processor_otlp = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT))
provider.add_span_processor(processor_otlp)
#provider.add_span_processor(processor_console)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(APP_NAME)
propagator = TraceContextTextMapPropagator()
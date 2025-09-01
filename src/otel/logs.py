import logging
import config

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

from opentelemetry.sdk._logs.export import (
    ConsoleLogExporter,
    SimpleLogRecordProcessor
)

from opentelemetry.semconv.attributes.service_attributes import (
    # Usando dessa forma os serviços vão seguir o padrão de nomenclatura do OpenTelemetry
    SERVICE_NAME,
    SERVICE_VERSION
)

from opentelemetry._logs import set_logger_provider



resource = Resource.create(
    {
        SERVICE_NAME: config.APP_NAME,
        SERVICE_VERSION: config.APP_VERSION
    }
)


provider = LoggerProvider(resource=resource)

console_exporter = ConsoleLogExporter()
otlp_exporter = OTLPLogExporter(
    endpoint=f'{config.OTLP_ENDPOINT}/v1/logs'
)

provider.add_log_record_processor(SimpleLogRecordProcessor(console_exporter))  
provider.add_log_record_processor(SimpleLogRecordProcessor(otlp_exporter)) 

set_logger_provider(provider)
otel_handler = LoggingHandler(logger_provider=provider)
otel_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(config.APP_NAME)
logger.addHandler(otel_handler)
logger.setLevel(logging.INFO)
#Evitar logs duplicados.
logger.propagate = False
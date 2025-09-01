import os
APP_NAME = os.getenv("APP_NAME", "app-a")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
TARGET_API_ENV = os.getenv("TARGET_API_ENV", "")
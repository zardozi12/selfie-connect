"""
Observability service with OpenTelemetry tracing and optional Sentry
"""
# Module scope
import os
import logging
from typing import Optional
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)
tracer: Optional[object] = None

def init_observability(app_name: str = "photovault"):
    if SENTRY_AVAILABLE and os.getenv("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.getenv("APP_ENV", "development"),
        )
        logger.info("Sentry initialized")

    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available")
        return

    resource = Resource.create({
        "service.name": app_name,
        "deployment.environment": os.getenv("APP_ENV", "development"),
    })
    tp = TracerProvider(resource=resource)
    trace.set_tracer_provider(tp)

    if os.getenv("JAEGER_AGENT_HOST"):
        exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        )
        tp.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("Jaeger tracing initialized")

    global tracer
    tracer = trace.get_tracer(__name__)

def instrument_fastapi(app):
    if OTEL_AVAILABLE:
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        logger.info("FastAPI instrumentation enabled")

@contextmanager
def trace_operation(name: str, **attrs):
    if tracer:
        with tracer.start_as_current_span(name) as span:
            for k, v in attrs.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                raise
    else:
        yield None
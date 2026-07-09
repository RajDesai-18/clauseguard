"""OpenTelemetry tracer provider setup.

Centralises tracing configuration so both the API process and the Celery
worker process initialise a tracer provider the same way. Instrumentation of
the frameworks themselves (FastAPI, Celery) is wired at each process's entry
point; this module only builds and installs the provider and its exporter.

Trace context propagates from an incoming HTTP request through the Celery
saga across the RabbitMQ boundary because CeleryInstrumentor injects the
active context into each task message on publish and extracts it on the
worker side. For that to work, both the API (the producer that dispatches the
pipeline) and the worker (which both consumes tasks and re-dispatches the
dynamic chords) must install a provider and instrument Celery.

Export target is configurable: with an OTLP endpoint set, spans go to that
collector (Jaeger in local dev); with the endpoint blank, spans print to the
console; with tracing disabled entirely, this module is a no-op.
"""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Guards against installing a second provider if setup is called more than
# once in the same process (e.g. reload, repeated worker signals).
_configured = False


def _build_exporter() -> SpanExporter:
    """Choose a span exporter based on configuration.

    Returns an OTLP gRPC exporter when an endpoint is configured, otherwise a
    console exporter so traces are still observable without a collector.

    Returns:
        The span exporter to attach to the provider.
    """
    endpoint = settings.otel_exporter_otlp_endpoint.strip()
    if endpoint:
        # Imported lazily so the OTLP extra is only required when actually used.
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        logger.info("OpenTelemetry exporting via OTLP to %s", endpoint)
        return OTLPSpanExporter(endpoint=endpoint, insecure=True)

    logger.info("OpenTelemetry OTLP endpoint unset; exporting spans to console")
    return ConsoleSpanExporter()


def setup_tracing(service_suffix: str) -> None:
    """Install a global tracer provider for the current process.

    Idempotent: a second call in the same process is a no-op. Does nothing at
    all when tracing is disabled via configuration.

    Args:
        service_suffix: Short label distinguishing this process in traces
            (e.g. "api" or "worker"), appended to the configured base service
            name so each process appears as its own service in the backend.
    """
    global _configured

    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false); skipping setup")
        return

    if _configured:
        return

    service_name = f"{settings.otel_service_name}-{service_suffix}"
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(_build_exporter()))
    trace.set_tracer_provider(provider)

    # Instrument Celery in every process that touches the queue. The API is a
    # producer (it dispatches the pipeline), and the worker is both consumer
    # and producer (it re-dispatches the dynamic chords), so both call this.
    # CeleryInstrumentor injects the active trace context into each task
    # message on publish and extracts it on the worker, carrying one trace
    # across the RabbitMQ boundary.
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()

    _configured = True
    logger.info("OpenTelemetry tracer provider installed for service=%s", service_name)

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

# Zero trace/span ids: what OpenTelemetry uses to mean "no active span".
_NO_TRACE_ID = f"{0:032x}"
_NO_SPAN_ID = f"{0:016x}"

# Guards against installing a second provider if setup is called more than
# once in the same process (e.g. reload, repeated worker signals).
_configured = False


class _TraceContextFilter(logging.Filter):
    """Guarantee every log record carries otelTraceID / otelSpanID.

    A format string that references these attributes must be able to resolve
    them on *every* record, including records emitted before instrumentation
    runs or by loggers the OTel record factory doesn't cover. This filter sets
    them unconditionally: the real ids when a span is active, all-zeros when
    not. That makes log formatting robust rather than dependent on the
    LoggingInstrumentor record factory having run first.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx is not None and ctx.is_valid:
            record.otelTraceID = f"{ctx.trace_id:032x}"
            record.otelSpanID = f"{ctx.span_id:016x}"
        else:
            record.otelTraceID = _NO_TRACE_ID
            record.otelSpanID = _NO_SPAN_ID
        return True


def install_log_trace_filter(target: logging.Logger | None = None) -> None:
    """Attach the trace-context filter to a logger's handlers.

    Idempotent: skips handlers that already have the filter. Call this after
    logging is configured (handlers exist) so every emitted record gets the
    otelTraceID / otelSpanID attributes the format string expects.

    Args:
        target: The logger whose handlers should get the filter. Defaults to
            the root logger, which covers the API's basicConfig handler; the
            Celery logging signals pass the specific logger they just
            configured so the filter lands on Celery's own handlers too.
    """
    log = target if target is not None else logging.getLogger()
    for handler in log.handlers:
        if not any(isinstance(f, _TraceContextFilter) for f in handler.filters):
            handler.addFilter(_TraceContextFilter())


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

    # Instrument the frameworks. This is wrapped so a missing or misbehaving
    # instrumentation package degrades observability rather than taking down
    # the process: tracing is best-effort and must never crash the app it
    # observes. The core provider above is already installed, so spans still
    # export even if an instrumentor here fails.
    try:
        # Celery: producer side in the API, consumer + producer in the worker.
        # Injects/extracts trace context across the RabbitMQ boundary so the
        # whole saga is one trace.
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()

        # Logging: adds otelTraceID / otelSpanID to records. We also install
        # our own filter (via install_log_trace_filter) which guarantees the
        # attributes exist even for records this instrumentor's factory doesn't
        # reach.
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception:
        logger.warning(
            "OpenTelemetry framework instrumentation partially failed; "
            "continuing with degraded observability",
            exc_info=True,
        )

    _configured = True
    logger.info("OpenTelemetry tracer provider installed for service=%s", service_name)

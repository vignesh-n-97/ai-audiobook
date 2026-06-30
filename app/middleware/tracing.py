"""OpenTelemetry tracing configuration."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.shared.config import Config


def configure_tracing(cfg: Config) -> None:
    """Set up OpenTelemetry OTLP exporter pointing at Tempo.

    Exports to cfg.otel_exporter_otlp_endpoint (default: http://localhost:4317).
    Service name is set to cfg.otel_service_name for Grafana filtering.
    """
    resource = Resource.create({"service.name": cfg.otel_service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=cfg.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def setup_tracing(service_name="ib-assistant"):
    """
    Настраивает OpenTelemetry для отправки трейсов в OTLP-совместимый коллектор (Jaeger).
    """
    # Устанавливаем ресурс (имя сервиса)
    resource = Resource(attributes={
        "service.name": service_name
    })

    # Создаем провайдер трейсов
    provider = TracerProvider(resource=resource)
    
    # Создаем экспортер, который будет отправлять данные в Jaeger
    # Убедитесь, что Jaeger OTLP gRPC ресивер доступен по этому адресу
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://jaeger:4317",  # Адрес Jaeger OTLP gRPC-ресивера
        insecure=True  # Используем insecure-канал, т.к. работаем внутри Docker
    )
    
    # Создаем процессор, который будет батчить и отправлять спаны
    processor = BatchSpanProcessor(otlp_exporter)
    
    # Добавляем процессор к провайдеру
    provider.add_span_processor(processor)
    
    # Устанавливаем глобальный провайдер трейсов
    trace.set_tracer_provider(provider)

# Вызываем настройку при импорте модуля, чтобы трейсинг был доступен везде
setup_tracing()

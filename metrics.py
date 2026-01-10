"""
Prometheus metrics for Catalog Service
"""

import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, Info

# Service info
catalog_service = Info("catalog_service", "Catalog service version")
catalog_service.info({"version": "1.0.0"})

# HTTP Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
)

http_errors_total = Counter(
    "http_errors_total", "Total HTTP errors", ["method", "endpoint", "error_type"]
)

# gRPC Metrics
grpc_requests_total = Counter(
    "grpc_requests_total", "Total gRPC requests", ["method", "status"]
)

grpc_request_duration_seconds = Histogram(
    "grpc_request_duration_seconds",
    "gRPC request latency",
    ["method"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
)

# Business Metrics
items_created_total = Counter("items_created_total", "Total items created")

items_by_status = Gauge("items_by_status", "Number of items by status", ["status"])

items_by_category = Gauge(
    "items_by_category", "Number of items by category", ["category"]
)

image_uploads_total = Counter(
    "image_uploads_total", "Total image uploads", ["status"]  # success, failed
)

image_upload_size_bytes = Histogram(
    "image_upload_size_bytes",
    "Size of uploaded images in bytes",
    buckets=[1024, 10240, 102400, 512000, 1048576, 5242880, 10485760],  # 1KB to 10MB
)

graphql_queries_total = Counter(
    "graphql_queries_total", "Total GraphQL queries", ["query_name", "status"]
)


# Helper context manager for timing operations
@contextmanager
def MetricsTimer(metric_histogram, *labels):
    """Context manager to time operations and record to histogram"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metric_histogram.labels(*labels).observe(duration)


# Helper functions
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics"""
    http_requests_total.labels(
        method=method, endpoint=endpoint, status=status_code
    ).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def record_grpc_request(method: str, status: str, duration: float):
    """Record gRPC request metrics"""
    grpc_requests_total.labels(method=method, status=status).inc()
    grpc_request_duration_seconds.labels(method=method).observe(duration)


def update_item_metrics(db):
    """Update item count metrics from database"""
    from sqlalchemy import func

    from models import ItemDB, ItemStatus

    # Count by status
    for status in ItemStatus:
        count = (
            db.query(func.count(ItemDB.id)).filter(ItemDB.status == status).scalar()
            or 0
        )
        items_by_status.labels(status=status.value).set(count)

    # Count by category
    category_counts = (
        db.query(ItemDB.category, func.count(ItemDB.id)).group_by(ItemDB.category).all()
    )

    for category, count in category_counts:
        items_by_category.labels(category=category).set(count)

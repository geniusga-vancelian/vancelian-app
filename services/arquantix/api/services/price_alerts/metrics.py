"""Observability metrics for the Price Alert Engine.

Thread-safe counters and timing stats exposed via get_metrics().
No external dependency (Prometheus/StatsD) — simple in-process counters
that can be scraped via a /admin/alerts/metrics endpoint.
"""
import threading
import time
from collections import defaultdict


class AlertMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.alerts_triggered_total = 0
        self.alerts_per_asset: dict[str, int] = defaultdict(int)
        self.trigger_latency_samples: list[float] = []
        self.notification_failures = 0
        self.ticks_processed = 0
        self.crossings_detected = 0
        self.cooldown_skips = 0
        self.dedup_skips = 0
        self.deferred_alerts = 0
        self.recurring_triggers = 0
        self.redis_errors = 0
        self.orders_executed = 0
        self.orders_failed = 0
        self.orders_partial_fills = 0
        self.orders_partial_remaining_volume = 0.0
        self.orders_retry_attempts = 0
        self.orders_skipped_price = 0
        self.processing_time_per_tick: list[float] = []

    def record_trigger(self, asset: str, count: int, latency_ms: float) -> None:
        with self._lock:
            self.alerts_triggered_total += count
            self.alerts_per_asset[asset] += count
            self.crossings_detected += count
            self.trigger_latency_samples.append(latency_ms)
            if len(self.trigger_latency_samples) > 1000:
                self.trigger_latency_samples = self.trigger_latency_samples[-500:]

    def record_tick(self, processing_ms: float = 0.0) -> None:
        with self._lock:
            self.ticks_processed += 1
            if processing_ms > 0:
                self.processing_time_per_tick.append(processing_ms)
                if len(self.processing_time_per_tick) > 1000:
                    self.processing_time_per_tick = self.processing_time_per_tick[-500:]

    def record_notification_failure(self) -> None:
        with self._lock:
            self.notification_failures += 1

    def record_cooldown_skip(self) -> None:
        with self._lock:
            self.cooldown_skips += 1

    def record_dedup_skip(self) -> None:
        with self._lock:
            self.dedup_skips += 1

    def record_deferred(self, count: int) -> None:
        with self._lock:
            self.deferred_alerts += count

    def record_recurring_trigger(self) -> None:
        with self._lock:
            self.recurring_triggers += 1

    def record_redis_error(self) -> None:
        with self._lock:
            self.redis_errors += 1

    def record_order_executed(self) -> None:
        with self._lock:
            self.orders_executed += 1

    def record_order_failed(self) -> None:
        with self._lock:
            self.orders_failed += 1

    def record_partial_fill(self) -> None:
        with self._lock:
            self.orders_partial_fills += 1

    def record_partial_remaining(self, remaining: float) -> None:
        with self._lock:
            self.orders_partial_remaining_volume += remaining

    def record_retry_attempt(self) -> None:
        with self._lock:
            self.orders_retry_attempts += 1

    def record_skipped_price(self) -> None:
        with self._lock:
            self.orders_skipped_price += 1

    def snapshot(self) -> dict:
        with self._lock:
            latencies = list(self.trigger_latency_samples)
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
            p99_lat = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0.0

            tick_times = list(self.processing_time_per_tick)
            avg_tick = sum(tick_times) / len(tick_times) if tick_times else 0.0

            return {
                "alerts_triggered_total": self.alerts_triggered_total,
                "alerts_per_asset": dict(self.alerts_per_asset),
                "ticks_processed": self.ticks_processed,
                "crossings_detected": self.crossings_detected,
                "cooldown_skips": self.cooldown_skips,
                "dedup_skips": self.dedup_skips,
                "deferred_alerts": self.deferred_alerts,
                "recurring_triggers": self.recurring_triggers,
                "notification_failures": self.notification_failures,
                "redis_errors": self.redis_errors,
                "orders_executed": self.orders_executed,
                "orders_failed": self.orders_failed,
                "orders_partial_fills": self.orders_partial_fills,
                "orders_partial_remaining_volume": round(self.orders_partial_remaining_volume, 8),
                "orders_retry_attempts": self.orders_retry_attempts,
                "orders_skipped_price": self.orders_skipped_price,
                "trigger_latency_avg_ms": round(avg_lat, 2),
                "trigger_latency_p99_ms": round(p99_lat, 2),
                "trigger_latency_samples": len(latencies),
                "processing_time_per_tick_avg_ms": round(avg_tick, 2),
            }


_metrics = AlertMetrics()


def get_metrics() -> AlertMetrics:
    return _metrics


class LatencyTimer:
    """Context manager to measure elapsed time in milliseconds."""
    def __init__(self):
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.monotonic() - self._start) * 1000.0

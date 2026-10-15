"""Circuit breaker per rail + retry logic with exponential backoff and jitter."""
import asyncio
import random
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Any, Optional

from app.core.logging import get_logger
from app.core.metrics import circuit_breaker_state

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"    # Normal operation
    OPEN = "OPEN"        # Failing, reject fast
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreaker:
    """Per-rail circuit breaker."""

    _instances: dict = {}

    def __init__(self, name: str, threshold: int = 5, timeout_seconds: int = 60):
        self.name = name
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    @classmethod
    def for_rail(cls, rail_code: str, threshold: int = 5, timeout_seconds: int = 60) -> "CircuitBreaker":
        if rail_code not in cls._instances:
            cls._instances[rail_code] = cls(rail_code, threshold, timeout_seconds)
        return cls._instances[rail_code]

    @classmethod
    def get_all_states(cls) -> dict:
        return {
            code: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "threshold": cb.threshold,
            }
            for code, cb in cls._instances.items()
        }

    def is_open(self) -> bool:
        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self.last_failure_time and (
                time.time() - self.last_failure_time > self.timeout_seconds
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker -> HALF_OPEN", extra={"rail": self.name})
                return False
            return True
        return False

    def record_success(self):
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker -> CLOSED", extra={"rail": self.name})
        self.state = CircuitState.CLOSED
        circuit_breaker_state.labels(rail=self.name).set(0)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    "Circuit breaker -> OPEN",
                    extra={"rail": self.name, "failures": self.failure_count},
                )
        self.state = CircuitState.OPEN
        circuit_breaker_state.labels(rail=self.name).set(1)

    def get_stats(self) -> dict:
        return {
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "timeout_seconds": self.timeout_seconds,
        }


def get_circuit_breaker(rail_code: str) -> CircuitBreaker:
    return CircuitBreaker.for_rail(rail_code)



class RailException(Exception):
    """Rail adapter error."""
    def __init__(self, rail: str, status_code: int, message: str):
        self.rail = rail
        self.status_code = status_code
        super().__init__(f"Rail {rail} error {status_code}: {message}")


class CircuitOpenException(Exception):
    """Raised when circuit breaker is open."""
    pass


CircuitBreakerOpenException = CircuitOpenException



async def call_with_retry(
    fn: Callable,
    *args,
    rail_code: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs,
) -> Any:
    """
    Call fn with exponential backoff + jitter and circuit breaker.
    """
    cb = circuit_breaker or CircuitBreaker.for_rail(rail_code)

    if cb.is_open():
        raise CircuitOpenException(
            f"Circuit breaker OPEN for rail {rail_code}. Fast-failing."
        )

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            result = await fn(*args, **kwargs)
            cb.record_success()
            return result
        except CircuitOpenException:
            raise
        except Exception as e:
            last_exc = e
            cb.record_failure()
            if attempt >= max_retries:
                break
            # Exponential backoff with full jitter
            delay = min(max_delay, base_delay * (2 ** attempt))
            jitter = delay * random.uniform(0, 0.5)
            wait = delay + jitter
            logger.warning(
                "Rail call failed, retrying",
                extra={
                    "rail": rail_code,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "wait_seconds": wait,
                    "error": str(e),
                },
            )
            await asyncio.sleep(wait)

    raise last_exc

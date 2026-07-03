"""
Circuit Breaker Service for external service resilience.

Provides circuit breaker pattern to prevent cascading failures when
external services (Ollama, PostgreSQL) are unavailable.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_FAILURES", "5"))
    success_threshold: int = int(os.getenv("CIRCUIT_BREAKER_SUCCESSES", "2"))
    timeout_seconds: float = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30"))
    half_open_max_calls: int = 3


@dataclass
class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    half_open_calls: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self):
        self._lock = asyncio.Lock()

    @property
    def is_available(self) -> bool:
        """Check if the circuit allows requests."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed to transition to half-open
            if time.time() - self.last_failure_time >= self.config.timeout_seconds:
                return True
            return False
        
        # HALF_OPEN: allow limited calls to test recovery
        return self.half_open_calls < self.config.half_open_max_calls

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Raises:
            CircuitBreakerOpenError: If circuit is open and not accepting calls
            Exception: Any exception from the underlying function
        """
        async with self._lock:
            if not self.is_available:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )

            # Transition to half-open if timeout passed
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls = max(0, self.half_open_calls - 1)
                
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
                logger.warning(f"Circuit breaker '{self.name}' reopened after half-open failure")
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPEN after {self.failure_count} failures"
                    )

    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "is_available": self.is_available,
        }

    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.half_open_calls = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global circuit breakers for external services
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            config=config or CircuitBreakerConfig()
        )
    return _circuit_breakers[name]


def get_all_circuit_breakers_status() -> list[dict]:
    """Get status of all circuit breakers."""
    return [cb.get_status() for cb in _circuit_breakers.values()]


async def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to closed state."""
    for cb in _circuit_breakers.values():
        await cb.reset()

"""Per-job cancellation and measurements, independent of the web interface."""

from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Event
from typing import Callable


class JobCancelled(Exception):
    pass


@dataclass
class RunContext:
    cancelled: Event = field(default_factory=Event)
    notify: Callable[[str, float], None] = lambda message, progress: None
    calls: int = 0
    cache_hits: int = 0
    model_seconds: float = 0


current_run: ContextVar[RunContext | None] = ContextVar("current_run", default=None)


def check_cancelled() -> None:
    context = current_run.get()
    if context and context.cancelled.is_set():
        raise JobCancelled("Cancelled between processing steps")


def report(message: str, progress: float) -> None:
    check_cancelled()
    context = current_run.get()
    if context:
        context.notify(message, progress)

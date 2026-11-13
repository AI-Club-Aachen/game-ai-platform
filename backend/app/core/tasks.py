import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class RecurringTask:
    name: str
    func: Callable[[], Awaitable[Any]]
    # A value, or a callable read before every run (e.g. lambda: settings.X).
    interval_seconds: float | Callable[[], float]
    task_obj: asyncio.Task | None = None
    is_enabled: bool | Callable[[], bool] = True

    def enabled(self) -> bool:
        return self.is_enabled() if callable(self.is_enabled) else self.is_enabled

    def interval(self) -> float:
        return self.interval_seconds() if callable(self.interval_seconds) else self.interval_seconds


class BackgroundTaskRunner:
    """
    A lightweight runner for recurring background tasks in FastAPI.
    """

    def __init__(self) -> None:
        self.tasks: list[RecurringTask] = []
        self._running = False

    def add_task(
        self,
        func: Callable[[], Awaitable[Any]],
        interval_seconds: float | Callable[[], float],
        name: str | None = None,
        is_enabled: bool | Callable[[], bool] = True,
    ) -> None:
        """
        Explicitly add an async function as a recurring background task.
        """
        task_name = name or func.__name__
        self.tasks.append(
            RecurringTask(name=task_name, func=func, interval_seconds=interval_seconds, is_enabled=is_enabled)
        )
        logger.info(f"Registered background task '{task_name}'")

    def start(self) -> None:
        """Start all registered background tasks."""
        if self._running:
            return
        self._running = True
        logger.info(f"Starting {len(self.tasks)} background task(s)...")

        for task in self.tasks:
            task.task_obj = asyncio.create_task(self._run_task_loop(task))

    async def stop(self) -> None:
        """Stop all running background tasks."""
        self._running = False
        logger.info("Stopping background tasks...")

        # Cancel tasks
        for task in self.tasks:
            if task.task_obj and not task.task_obj.done():
                task.task_obj.cancel()

        # Wait for cancellation to complete
        running_tasks = [t.task_obj for t in self.tasks if t.task_obj]
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)

    async def _run_task_loop(self, task: RecurringTask) -> None:
        """The main loop for a single recurring task."""
        while self._running:
            try:
                if task.enabled():
                    logger.debug(f"Running background task: {task.name}")
                    await task.func()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Error in background task {task.name}")

            # Wait for next interval or cancellation, responsive to dynamic interval changes
            try:
                waited = 0.0
                # Sleep in short increments so that if interval_seconds is reduced, we wake up sooner.
                while waited < task.interval():
                    if not self._running:
                        break
                    await asyncio.sleep(0.5)
                    waited += 0.5
            except asyncio.CancelledError:
                break

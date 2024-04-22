import asyncio
import logging
from threading import Lock
from typing import Coroutine

DEFAULT_MAX_TASKS_PER_SECOND = 2


class AsyncIORateLimiter:
    """
    A thread-safe class that keeps track of a set of max running asyncio tasks
    for rate limiting purposes.
    """

    RATE_LIMIT_WINDOW = 1  # seconds

    _lock = Lock()

    def __init__(self, max_tasks_per_second: int = DEFAULT_MAX_TASKS_PER_SECOND):
        self._max_tasks_per_second = max_tasks_per_second
        self._running_tasks: set[asyncio.Task] = set()

    def overwrite_max_tasks_per_second(self, max_tasks_per_sec: int):
        """Overwrite max tasks per second window allowance.

        Note:
            🚨 This function should be used for testing purposes only as
               it defeats the purpose of having a thread-safe rate limiter.

        Raises:
            ValueError: If `max_tasks_per_sec` is less than 1.
        """
        if max_tasks_per_sec < 1:
            raise ValueError(
                f"max_tasks_per_sec requires a value of at least 1, {max_tasks_per_sec} was provided."
            )
        self._max_tasks_per_second = max_tasks_per_sec

    def discard_running_task(self, task: asyncio.Task):
        """
        Discards a running task.
        """
        with self._lock:
            self._running_tasks.discard(task)

    async def run_rate_limited_tasks(self, coros: list[Coroutine]) -> list[any]:
        """Rate limit a number of concurrent tasks per second.

        Note:
            The default 1-second rate limit window (delay per cycle) could be abstracted as an argument for greater extensibility.
            Further failed task retry logic/exception handling could be implemented at the expense of added complexity.

        Args:
            coros: List of coroutines to run concurrently as tasks.
            max_tasks_per_sec: Maximum tasks per second.

        Returns:
            List of tasks results.

        Raises:
            ExceptionGroup: If a task fails, it bubbles up the exception, and cancels all running tasks.
        """
        scheduled_tasks: list[asyncio.Task] = []

        async with asyncio.TaskGroup() as tg:  # TaskGroup included in Python >= 3.11
            task_group_cycle = 0
            while True:
                # Total pending coroutines to be scheduled
                total_pending = len(coros) - len(scheduled_tasks)

                # Prevent race conditions with self._running_tasks total slots available.
                with self._lock:
                    # Total slots available for the current cycle (rate limit per second)
                    total_slots_available = self._max_tasks_per_second - len(
                        self._running_tasks
                    )

                    # When `total_pending` < `total_slots_available`,
                    # we will finish scheduling all tasks and won't need to rate limit anymore.
                    remaining_to_schedule = min(total_slots_available, total_pending)

                    # Schedule coroutines to start running concurrently in the task group.
                    for _ in range(remaining_to_schedule):
                        next_coro_offset = len(scheduled_tasks)
                        task = tg.create_task(coros[next_coro_offset])
                        scheduled_tasks.append(task)
                        self._running_tasks.add(task)
                        task.add_done_callback(self.discard_running_task)

                task_group_cycle += 1
                logging.debug(
                    "Task Group Cycle #%d: total_running_tasks=%d total_scheduled_tasks=%d total_remaining_coros=%d",
                    task_group_cycle,
                    len(self._running_tasks),
                    len(scheduled_tasks),
                    len(coros) - len(scheduled_tasks),
                )

                # Wait for RATE_LIMIT_WINDOW if there are any pending tasks to be scheduled,
                # otherwise break the scheduling loop and wait for the task group to finish.
                if len(scheduled_tasks) < len(coros):
                    logging.debug(
                        "Task Group Cycle #%d: Rate limiting for %d second before scheduling next pending tasks.",
                        task_group_cycle,
                        self.RATE_LIMIT_WINDOW,
                    )
                    await asyncio.sleep(self.RATE_LIMIT_WINDOW)
                else:
                    break

            logging.debug("Awaiting for task group to complete.")

        logging.debug("All tasks successfully completed.")
        return [task.result() for task in scheduled_tasks]

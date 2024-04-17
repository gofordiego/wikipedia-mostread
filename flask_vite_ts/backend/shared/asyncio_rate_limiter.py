import asyncio
import logging
from threading import Lock
from typing import Coroutine


class AsyncIORateLimiter:
    """
    A thread-safe singleton class that keeps track of a set of max running asyncio tasks
    for rate limiting purposes.
    """

    MAX_RUNNING_TASKS = 2

    RATE_LIMIT_WINDOW = 1  # 1 seconds

    _instance = None  # The shared instance
    _lock = Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._running_tasks: set[asyncio.Task] = set()

    def total_running_tasks(self) -> int:
        return len(self._running_tasks)

    def add_running_task(self, task: asyncio.Task):
        """
        Tracks a new running task.
        """
        with self._lock:
            self._running_tasks.add(task)

    def discard_running_task(self, task: asyncio.Task):
        """
        Discards a running task.
        """
        with self._lock:
            self._running_tasks.discard(task)

    async def run_rate_limited_tasks(
        self, coros: list[Coroutine], max_tasks_per_sec: int
    ) -> list[any]:
        """Rate limit a number of concurrent tasks per second.

        Note:
            The default 1-second delay per cycle could be abstracted as an argument for greater extensibility.
            Further failed task retry logic/exception handling could be implemented at the expense of added complexity.

        Args:
            coros: List of coroutines to run concurrently as tasks.
            max_tasks_per_sec: Maximum tasks per second.

        Returns:
            List of tasks results.

        Raises:
            ValueError: If `max_tasks_per_sec` is less than 1.
            ExceptionGroup: If a task fails, it bubbles up the exception, and cancels all running tasks.
        """
        if max_tasks_per_sec < 1:
            raise ValueError(
                f"max_tasks_per_sec requires a value of at least 1, {max_tasks_per_sec} was provided."
            )

        scheduled_tasks: list[asyncio.Task] = []

        async with asyncio.TaskGroup() as tg:  # TaskGroup included in Python >= 3.11
            task_group_cycle = 0
            while True:
                # Total pending coroutines to be scheduled
                total_pending = len(coros) - len(scheduled_tasks)

                # Total slots available for the current cycle (rate limit per second)
                total_slots_available = max_tasks_per_sec - self.total_running_tasks()

                # When `total_pending` < `total_slots_available`,
                # we will finish scheduling all tasks and won't need to rate limit anymore.
                remaining_to_schedule = min(total_slots_available, total_pending)

                # Schedule coroutines to start running concurrently in the task group.
                for _ in range(remaining_to_schedule):
                    next_coro_offset = len(scheduled_tasks)
                    task = tg.create_task(coros[next_coro_offset])
                    scheduled_tasks.append(task)
                    self.add_running_task(task)
                    task.add_done_callback(self.discard_running_task)

                task_group_cycle += 1
                logging.debug(
                    "Task Group Cycle #%d: total_running_tasks=%d total_scheduled_tasks=%d total_remaining_coros=%d",
                    task_group_cycle,
                    self.total_running_tasks(),
                    len(scheduled_tasks),
                    len(coros) - len(scheduled_tasks),
                )

                # Wait for 1 second if there are any pending tasks to be scheduled,
                # otherwise break the scheduling loop and wait for the task group to finish.
                if len(scheduled_tasks) < len(coros):
                    logging.debug(
                        "Task Group Cycle #%d: Rate limiting for 1 second before scheduling next pending tasks.",
                        task_group_cycle,
                    )
                    # NOTE: The 1 second delay could be abstracted as an argument.
                    await asyncio.sleep(self.RATE_LIMIT_WINDOW)
                else:
                    break

            logging.debug("Awaiting for task group to complete.")

        logging.debug("All tasks successfully completed.")
        return [task.result() for task in scheduled_tasks]

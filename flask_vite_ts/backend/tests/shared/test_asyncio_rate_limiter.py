import asyncio
from collections import namedtuple
import logging
import os
import sys
from unittest import IsolatedAsyncioTestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.asyncio_rate_limiter import AsyncIORateLimiter


class AsyncIORateLimiterTests(IsolatedAsyncioTestCase):

    def setUp(self):
        self.aio_rate_limiter = AsyncIORateLimiter()

    async def test_run_rate_limited_tasks_success(self):
        """Test `run_rate_limited_tasks` successful results test cases.

        Note:
            Testing 'expected_time' in production CI might be flaky due to variable CPU load,
            here we mainly use it for illustrative debugging purposes

            Case Example:
            ```
                max_tasks_per_second=2
                run_rate_limited_tasks(
                    coros=[self._delay(1), self._delay(2), self._delay(3)]
                )

                expected_results=[1, 2, 3]
                expected_time=4  (1-second cycles)

                     -----------------------------------------
                    | Cycle 1  | Cycle 2  | Cycle 3 | Cycle 4 |
                    |----------|----------|---------|---------|
            Slot A: | delay(1) | delay(3) |   ...   |   ...   |
            Slot B: | delay(2) |   ...    |   Free  |   Free  |
                     -----------------------------------------
            ```
        """
        assertion_time_delta = 0.5  # seconds

        Case = namedtuple(
            "Case",
            (
                "coros",
                "max_tasks_per_sec",
                "description",
                "expected_results",
                "expected_time",
            ),
        )
        cases = [
            Case(
                [self._delay(3), self._delay(2), self._delay(1)],
                1,
                "1 running, 2 queued",
                [3, 2, 1],
                6,
            ),
            Case(
                [self._delay(1), self._delay(2), self._delay(3)],
                2,
                "2 running, 1 queued",
                [1, 2, 3],
                4,
            ),
            Case(
                [self._delay(1), self._delay(2), self._delay(3)],
                3,
                "3 running, 0 queued",
                [1, 2, 3],
                3,
            ),
        ]

        for c in cases:
            loop = asyncio.get_running_loop()
            start = loop.time()
            self.aio_rate_limiter.overwrite_max_tasks_per_second(c.max_tasks_per_sec)
            results = await self.aio_rate_limiter.run_rate_limited_tasks(coros=c.coros)
            total_time = loop.time() - start
            self.assertEqual(
                results, c.expected_results, f"Test results for {c.description}"
            )
            # Asserting almost equal expected and got total run time.
            self.assertAlmostEqual(
                total_time,
                c.expected_time,
                None,
                f"Test expected time {c.description}",
                assertion_time_delta,
            )

    async def test_run_rate_limited_tasks_error(self):
        """Test `run_rate_limited_tasks` error exceptions."""

        Case = namedtuple("Case", ("coros", "max_tasks_per_sec", "expected_exception"))
        cases = [
            Case([], 0, ValueError),
            Case(
                [self._delay(1, raise_exception=True), self._delay(1)],
                2,
                ExceptionGroup,
            ),
        ]

        for c in cases:
            with self.assertRaises(c.expected_exception):
                self.aio_rate_limiter.overwrite_max_tasks_per_second(
                    c.max_tasks_per_sec
                )
                await self.aio_rate_limiter.run_rate_limited_tasks(coros=c.coros)

    async def _delay(self, secs: int, raise_exception=False) -> int:
        """Delays `secs` seconds in returning the same argument."""

        logging.debug("Delay (%d secs). Started", secs)

        if raise_exception:
            raise Exception("Coroutine Error")

        for i in range(secs):
            # For testing purposes wait less than a second to make it to next scheduling cycle.
            await asyncio.sleep(0.95)
            logging.debug("Delay (%d secs). Passed %d seconds", secs, i + 1)

        logging.debug("Delay (%d secs). Completed", secs)

        return secs


if __name__ == "__main__":
    # Leaving this to facilitate debugging.
    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )
    main()

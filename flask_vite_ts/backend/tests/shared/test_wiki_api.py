from collections import namedtuple
from datetime import datetime, timedelta
import logging
import os
import sys
from unittest import IsolatedAsyncioTestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import shared.wiki_api as wiki_api
from tests.shared.expected_results_wiki_api import *


class WikiAPITests(IsolatedAsyncioTestCase):

    def setUp(self):
        self.wiki_api = wiki_api.WikiAPI()

    async def test_fetch_most_read_articles_success(self):
        """Test `fetch_most_read_articles` success."""

        # Calculate tomorrow's date for testing
        tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        Case = namedtuple(
            "Case", ("lang_code", "start", "end", "test_message", "expected_results")
        )
        cases = [
            Case(
                "es",
                "2024-02-19",
                "2024-02-19",
                "Test 1-day range Spanish Wikipedia",
                EXPECTED_MOST_READ_ES_20240219,
            ),
            Case(
                "it",
                "2024-02-19",
                "2024-02-20",
                "Test 2-day range Italian Wikipedia",
                EXPECTED_MOST_READ_EN_20240219_20240220,
            ),
            # Tomorrow's page views do not exist yet, however API returns 200 response for other scheduled Featured Content.
            Case(
                "en", tomorrow, tomorrow, "Test future date", {"data": [], "errors": []}
            ),
        ]

        for c in cases:
            results = await self.wiki_api.fetch_most_read_articles(
                lang_code=c.lang_code, start=c.start, end=c.end
            )
            self.assertEqual(results, c.expected_results, "Test returned articles")

    async def test_fetch_most_read_articles_raised_exceptions(self):
        """Test `fetch_most_read_articles` raised exceptions."""

        Case = namedtuple("Case", ("lang_code", "start", "end", "expected_exception"))
        cases = [
            Case("en", "2024-19-02", "2024-02-19", wiki_api.InvalidStartDateError),
            Case("es", "2024-02-19", "2024-19-02", wiki_api.InvalidEndDateError),
            Case("es", "2024-02-20", "2024-02-19", wiki_api.InvalidDateRangeError),
            Case(
                "hax0r.com/pwned",
                "2024-02-19",
                "2024-02-19",
                wiki_api.InvalidLanguageCodeError,
            ),
        ]

        for c in cases:
            with self.assertRaises(c.expected_exception) as cm:
                await self.wiki_api.fetch_most_read_articles(
                    lang_code=c.lang_code, start=c.start, end=c.end
                )
            # Check also the base module error is reported correctly.
            self.assertIsInstance(cm.exception, wiki_api.WikiAPIError)

    async def test_fetch_most_read_articles_response_errors(self):
        """Test `fetch_most_read_articles` response errors."""

        Case = namedtuple(
            "Case",
            (
                "lang_code",
                "start",
                "end",
                "expected_error_url",
                "expected_error_message",
            ),
        )
        cases = [
            # Host fails for non-existent language codes.
            Case(
                "valyrian",
                "2024-02-19",
                "2024-02-19",
                "https://valyrian.wikipedia.org/api/rest_v1/feed/featured/2024/02/20",
                str(wiki_api.WikipediaConnectionError()),
            ),
            # A thousand years in the future response an error response.
            Case(
                "en",
                "3024-02-19",
                "3024-02-19",
                "https://en.wikipedia.org/api/rest_v1/feed/featured/3024/02/20",
                str(wiki_api.WikipediaResponseError()),
            ),
        ]

        for c in cases:
            results = await self.wiki_api.fetch_most_read_articles(
                lang_code=c.lang_code, start=c.start, end=c.end
            )
            expected_results = {
                "data": [],
                "errors": [
                    {
                        "url": c.expected_error_url,
                        "message": c.expected_error_message,
                    },
                ],
            }
            self.assertEqual(results, expected_results, "Test returned errors")


if __name__ == "__main__":
    # Leaving this to facilitate debugging.
    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )
    main()

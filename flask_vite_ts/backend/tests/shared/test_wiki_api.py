from collections import namedtuple
from datetime import datetime, timedelta
import json
import logging
import os
import sys
from unittest import IsolatedAsyncioTestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import shared.wiki_api as wiki_api
from tests.shared.expected_results_wiki_api import *


class TestCache(wiki_api.WikiCache):
    """This is a subclass of WikiCache used to store WikiAPI responses in a dictionary
    to ease testing validation.
    """

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[str, str] = {}

    def get(self, url: str) -> wiki_api.WikiAPIResponse:
        cached_response = self._cache.get(url)
        if cached_response:
            return wiki_api.WikiAPIResponse(url, True, cached_response, None)
        return None

    def put(self, wiki_resp: wiki_api.WikiAPIResponse):
        assert (
            wiki_resp.url
            and wiki_resp.status_ok
            and wiki_resp.text
            and not wiki_resp.exception
        )
        self._cache[wiki_resp.url] = wiki_resp.text


class WikiAPITests(IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_cache = TestCache()
        self.wiki_api = wiki_api.WikiAPI(optional_cache=self.test_cache)

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

        # Cache validation
        expected_cache_keys = set(
            [
                "https://es.wikipedia.org/api/rest_v1/feed/featured/2024/02/20",
                "https://it.wikipedia.org/api/rest_v1/feed/featured/2024/02/20",
                "https://it.wikipedia.org/api/rest_v1/feed/featured/2024/02/21",
            ]
        )
        # 🚨 Note that https://en.wikipedia.org/api/rest_v1/feed/featured/TOMORROW never contains
        # the mostread articles object, because we cannot travel to future to know what people will read,
        # therefore we will not cache yet that response.
        self.assertEqual(set(self.test_cache._cache.keys()), expected_cache_keys)

        # Cache content
        raw_response = self.test_cache._cache.get(
            "https://es.wikipedia.org/api/rest_v1/feed/featured/2024/02/20", ""
        )
        self.assertEqual(json.loads(raw_response)["mostread"]["date"], "2024-02-19Z")

        # Test results after cached response hit.
        results = await self.wiki_api.fetch_most_read_articles(
            lang_code=cases[0].lang_code, start=cases[0].start, end=cases[0].end
        )
        self.assertEqual(
            results, cases[0].expected_results, "Test returned articles from cache"
        )

    async def test_no_cache_fetch_most_read_articles_success(self):
        """Test no cache layer `fetch_most_read_articles` success."""
        no_cache_wiki_api = wiki_api.WikiAPI()
        results = await no_cache_wiki_api.fetch_most_read_articles(
            lang_code="es", start="2024-02-19", end="2024-02-19"
        )
        self.assertEqual(results, EXPECTED_MOST_READ_ES_20240219)

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

        # Validate cache remained empty
        self.assertFalse(len(self.test_cache._cache))

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

        # Validate cache remained empty
        self.assertFalse(len(self.test_cache._cache))


if __name__ == "__main__":
    # Leaving this to facilitate debugging.
    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )
    main()

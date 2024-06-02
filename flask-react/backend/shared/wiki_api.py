from collections import namedtuple
from datetime import datetime, timedelta
import httpx
import json
import logging
import re
from typing import Callable

from shared.asyncio_rate_limiter import AsyncIORateLimiter


WikiAPIResponse = namedtuple(
    "WikiAPIResponse", ["url", "status_ok", "text", "exception"]
)


class WikiCache:
    """This abstract class acts as an interface to the caching layer,
    which can be implemented in anything like a local dictionary or database.

    Note:
        We could also implement a `multi_get` function to offer a group fetch if the
        caching layer has this capability.
    """

    def get(self, url: str) -> WikiAPIResponse:
        raise NotImplementedError

    def put(self, resp: WikiAPIResponse):
        raise NotImplementedError


class WikiAPI:

    MAX_REQUESTS_PER_SEC = 100  # Wikipedia API Rate Limit

    MAX_RESPONSE_RESULTS = 5000

    DEFAULT_USER_AGENT = "test"

    def __init__(
        self,
        optional_cache: WikiCache = None,
        user_agent: str = DEFAULT_USER_AGENT,
        access_token: str = None,
    ) -> None:
        self.optional_cache = optional_cache
        self.user_agent = user_agent
        self.access_token = access_token
        self.aio_rate_limiter = AsyncIORateLimiter(
            max_tasks_per_second=self.MAX_REQUESTS_PER_SEC
        )

    # MARK: - Public Functions

    async def fetch_most_read_articles(
        self, lang_code: str, start: str, end: str, results_limit=MAX_RESPONSE_RESULTS
    ) -> list[dict[str, any]]:
        """Fetches the most read articles from Wikipedia by supported language code and date range.

        This function fetches data concurrently from Wikipedia's Feed API Featured Content for each day
        on the specified range. The Feed API returns the top 50 featured articles (sometimes less as it filters
        out pages irrelevant articles like Wikipedia's homepage). The Feed API was elected over the REST API
        due to its filtering capabilities and focus on top 50 articles instead of top 1000.

        Args:
            lang_code: Wikipedia language code
            start: Start day to retrieve from. Format: YYYY-MM-DD
            end: Last day (inclusive interval). Format: YYYY-MM-DD

        Returns:
            Sorted (descending) list of most read articles with total views and views history by date,
            and errors if any occurred for a URL.
                ```
                e.g. {
                    data: [{page: 'https://en.wikipedia...', total_views: 9000, view_history: [{date: '2020-12-30', views: 4500}], ...],
                    errors: [{url: 'https://en.wikipedia...', message: 'Error connecting...'}, ...]
                }
                ```

        Raises:
            InvalidStartDateError: If `start` string date is not formatted correctly.
            InvalidEndDateError: If `end` string date is not formatted correctly.
            InvalidDateRangeError: If `end` date is before `start` date.
            InvalidLanguageCodeError: If language code contains invalid characters.
        """
        start_date, end_date = self._parse_formatted_date_range(start, end)

        # 🚨 Counterintuitively the Feed API Featured Content needs to be queried one day in the future.
        #    to return the wanted date's most read articles.
        shifted_start_date = start_date + timedelta(days=1)
        shifted_end_date = end_date + timedelta(days=1)

        wiki_api_responses = await self._fetch_feed_api_featured_content_responses(
            lang_code, shifted_start_date, shifted_end_date
        )

        successful_featured_content_responses = []
        error_responses = []
        for wiki_resp in wiki_api_responses:
            if wiki_resp.exception:
                # Unexpected expection
                error_responses.append(
                    self._format_wiki_api_error(wiki_resp.url, str(wiki_resp.exception))
                )
            elif not wiki_resp.status_ok:
                # Unexpected status code on API response
                error_responses.append(
                    self._format_wiki_api_error(
                        wiki_resp.url, str(WikipediaResponseError())
                    )
                )
            else:
                # Successful API response
                successful_featured_content_responses.append(wiki_resp.text)

        most_read_articles = self._reduce_and_sort_featured_content_most_read_articles(
            successful_featured_content_responses
        )

        if len(most_read_articles) > results_limit:
            url = ""
            message = f"Limited response to {results_limit} out of {len(most_read_articles) } results."
            error_responses.insert(0, self._format_wiki_api_error(url, message))

        return {
            "data": most_read_articles[:results_limit],
            "errors": error_responses,
        }

    # MARK: - Private Functions

    def _format_wiki_api_error(self, url: str, message: str) -> dict[str, str]:
        return {"url": url, "message": message}

    def _try_cache_get(self, url: str) -> WikiAPIResponse:
        if isinstance(self.optional_cache, WikiCache):
            return self.optional_cache.get(url)
        return None

    def _try_cache_put(self, wiki_resp: WikiAPIResponse):
        if isinstance(self.optional_cache, WikiCache):
            self.optional_cache.put(wiki_resp)

    def _validate_featured_content_mostread_response(
        self, resp: WikiAPIResponse
    ) -> bool:
        """Validate `resp` state and that its text actually contains
        the mostread article object from the Featured Content API.
        """
        if resp.exception or not resp.status_ok or not resp.url or not resp.text:
            return False
        featured_content = json.loads(resp.text)
        return len(featured_content.get("mostread", {})) > 0

    async def _fetch_feed_api_featured_content_responses(
        self, lang_code: str, start_date: datetime, end_date: datetime
    ) -> list[WikiAPIResponse]:
        """Gets a list of responses from Wikipedia's Feed API Featured Content for a date range.

        This function runs concurrent API requests taking advantage of HTTP/2
        and throttles `MAX_REQUESTS_PER_SEC` active requests per second.

        Note:
            🚨 This function handles dates as specified on the Wikipedia Feed API:
                e.g. To get featured content for 2023/12/31, we need to request one day forward (2024/01/01).

        Args:
            lang_code: Wikipedia language code.
            start_date: Start day of range.
            end_date: Last day of range (inclusive).

        Returns:
            List of Feed API Featured Content responses.
              e.g. `[WikiAPIResponse(url, response, exception), ... ]`
        """

        api_urls = self._build_feed_api_featured_content_urls(
            lang_code, start_date, end_date
        )

        # Get cached responses and filter out missing ones for subsequent API fetch calls.
        cache_hit_responses = []
        cache_missed_urls = []
        for url in api_urls:
            cached_response = self._try_cache_get(url)
            if cached_response:
                logging.info("CACHE HIT: %s" % url)
                cache_hit_responses.append(cached_response)
            else:
                cache_missed_urls.append(url)

        if not cache_missed_urls:
            return cache_hit_responses
        else:
            # Request Wikipedia Feed API for Featured Content concurrently
            # using HTTP/2 and limiting active requests per second.
            headers = self._build_api_request_headers()
            async with httpx.AsyncClient(http2=True, headers=headers) as client:
                fetch_tasks = [
                    self.fetch_wiki_api_response(
                        url,
                        client,
                        response_validator=self._validate_featured_content_mostread_response,
                    )
                    for url in cache_missed_urls
                ]
                fetched_responses: list[WikiAPIResponse] = (
                    await self.aio_rate_limiter.run_rate_limited_tasks(
                        coros=fetch_tasks
                    )
                )
            return cache_hit_responses + fetched_responses

    async def fetch_wiki_api_response(
        self,
        url: str,
        client: httpx.AsyncClient,
        response_validator: Callable[[WikiAPIResponse], bool],
    ) -> WikiAPIResponse:
        try:
            logging.info("Fetching: %s" % url)
            http_response = await client.get(url)
            wiki_resp = WikiAPIResponse(
                url, http_response.status_code == 200, http_response.text, None
            )
            # Validate response eligibility for caching:
            # e.g. Cache Featured Content response only if mostread articles object is present.
            if response_validator(wiki_resp):
                logging.info("CACHE PUT: %s" % url)
                self._try_cache_put(wiki_resp)
            return wiki_resp
        except httpx.HTTPError as e:
            logging.error(
                "Wikipedia API Connection Error for request: %s. Error: %s",
                e.request,
                e,
            )
            return WikiAPIResponse(url, False, None, WikipediaConnectionError())
        except Exception as e:
            return WikiAPIResponse(url, False, None, e)

    def _reduce_and_sort_featured_content_most_read_articles(
        self, featured_content_responses: list[str]
    ) -> list[list[str, any]]:
        """Reduces and sorts (DESC) most read articles total views from Wikipedia's Feed API Featured Content responses.

        Args:
            featured_content_responses: List of Feed API Featured Content responses.
                e.g. `['{"tfa": ..., "mostread": ...', ...]`

        Returns:
            Sorted list of most read articles with total views and views history by date.
                e.g. `[{page: 'https://en.wikipedia...', total_views: 9000, view_history: [{date: '2020-12-30', views: 4500}], ...]`
                🚨 Note that views_history only contains views for days where the article was featured in the day's top 50.

        Raises:
            WikipediaContentProcessingError: If there's a JSON decoding or content integrity errors in `featured_content_responses`.
        """
        # Structure: {pageid: {page, total_views, view_history: [date, views]}, ...}
        articles_stats: dict[int, dict[str, any]] = {}

        for response in featured_content_responses:
            try:
                json_content = json.loads(response)
            except json.decoder.JSONDecodeError:
                logging.error("Invalid featured content JSON response: %s", response)
                raise WikipediaContentProcessingError

            # "mostread.articles" might not be present if the requested date was today (still measuring views).
            if not "mostread" in json_content:
                continue

            try:
                # Parse date from response
                views_date = datetime.strptime(
                    json_content["mostread"]["date"], "%Y-%m-%dZ"
                )
                for article in json_content["mostread"]["articles"]:
                    page_id = int(article["pageid"])
                    views = int(article["views"])

                    # Prepare new article stats slot for aggregation.
                    if page_id not in articles_stats:
                        articles_stats[page_id] = {
                            # We could add more article details like "description" or "thumbnail".
                            "page": article["content_urls"]["desktop"]["page"],
                            "total_views": 0,
                            "view_history": [],
                        }

                    articles_stats[page_id]["total_views"] += views

                    # Aggregate view history using ISO 8601 Date format.
                    articles_stats[page_id]["view_history"].append(
                        {
                            "date": views_date.strftime("%Y-%m-%d"),
                            "views": views,
                        }
                    )
            except KeyError as e:
                logging.error(
                    "Missing key in article object (%s) from Feed API response: %s",
                    e,
                    response,
                )
                raise WikipediaContentProcessingError
            except ValueError as e:
                logging.error(
                    "Unexpected value in article object (%s) from Feed API response: %s",
                    e,
                    response,
                )
                raise WikipediaContentProcessingError

        # Extract and sort article URLs by total views in descending order.
        ranked_pageids = [
            item[0]
            for item in sorted(
                articles_stats.items(),
                key=lambda item: item[1]["total_views"],
                reverse=True,
            )
        ]

        # Build a sorted array of article_stats objects:
        # e.g. [{page, total_views, view_history}, ...]
        return [
            {**{"pageid": page_id}, **articles_stats[page_id]}
            for page_id in ranked_pageids
        ]

    def _build_feed_api_featured_content_urls(
        self, lang_code: str, start_date: datetime, end_date: datetime
    ) -> list[str]:
        """Builds a date range list of Wikipedia's Feed API Featured Content URLs.

        Args:
            lang_code: Wikipedia language code.
            start_date: Start day of range.
            end_date: Last day of range (inclusive).

        Returns:
            List of API URLs.
                e.g. `[https://en.wikipedia.org/api/rest_v1/feed/featured/2024/02/19, ...]`

        Raises:
            InvalidLanguageCodeError: If language code contains invalid characters.
        """
        if not self._validate_language_code(lang_code):
            raise InvalidLanguageCodeError
        urls: list[str] = []

        cur_day = start_date
        while cur_day <= end_date:
            formatted_date = cur_day.strftime("%Y/%m/%d")
            urls.append(
                f"https://{lang_code}.wikipedia.org/api/rest_v1/feed/featured/{formatted_date}"
            )
            cur_day += timedelta(days=1)

        return urls

    def _validate_language_code(self, lang_code: str) -> bool:
        """Checks that a language code only contains letters, numbers or dashes.

        See Wikipedia languages here: https://wikistats.wmcloud.org/display.php?t=wp
        """
        # Useful to flag potential harmful characters when forming an API URL.
        pattern = r"^[a-zA-Z0-9-]+$"
        return bool(re.match(pattern, lang_code))

    def _parse_formatted_date_range(
        self, start: str, end: str
    ) -> tuple[datetime, datetime]:
        """Parses YYYYMMDD formatted string arguments into datetime objects.

        Returns:
            Tuple (`start`, `end`) as datetime values.

        Raises:
            InvalidStartDateError: If `start` string date is not formatted correctly.
            InvalidEndDateError: If `end` string date is not formatted correctly.
            InvalidDateRangeError: If `end` date is before `start` date.
        """
        date_arg_format = "%Y-%m-%d"

        try:
            start_date = datetime.strptime(start, date_arg_format)
        except ValueError:
            raise InvalidStartDateError

        try:
            end_date = datetime.strptime(end, date_arg_format)
        except ValueError:
            raise InvalidEndDateError

        if start_date > end_date:
            raise InvalidDateRangeError

        return (start_date, end_date)

    def _build_api_request_headers(self) -> dict[str, str]:
        """Builds the headers for a Wikipedia API request to indicate:
        - User Agent
        - Authorization Access Token (Optional)

        Returns:
            Dictionary with the request headers.
        """
        headers = {"user-agent": self.user_agent}
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"

        return headers


# MARK: - Exceptions


class WikiAPIError(Exception):
    """Base class for all exceptions from this module."""


class InvalidArticlePageError(WikiAPIError):
    def __init__(self) -> None:
        message = "Invalid Wikipedia article page."
        super().__init__(message)


class InvalidLanguageCodeError(WikiAPIError):
    def __init__(self) -> None:
        message = "Invalid Wikipedia language code."
        super().__init__(message)


class InvalidStartDateError(WikiAPIError):
    def __init__(self) -> None:
        message = "Invalid start date."
        super().__init__(message)


class InvalidEndDateError(WikiAPIError):
    def __init__(self) -> None:
        message = "Invalid end date."
        super().__init__(message)


class InvalidDateRangeError(WikiAPIError):
    def __init__(self) -> None:
        message = "Invalid date range, start date should be before the end date."
        super().__init__(message)


class WikipediaConnectionError(WikiAPIError):
    def __init__(self) -> None:
        message = "Error connecting to the Wikipedia server."
        super().__init__(message)


class WikipediaResponseError(WikiAPIError):
    """
    Note: We could create a secondary error to be more explicit about being rate limited,
          in addition to receiving a non-200 OK response.
    """

    def __init__(self) -> None:
        message = (
            "Wikipedia server returned an unexpected response, could be rate limited."
        )
        super().__init__(message)


class WikipediaContentProcessingError(WikiAPIError):
    def __init__(self) -> None:
        message = "Unexpected error while processing the content of a response from the Wikipedia API."
        super().__init__(message)

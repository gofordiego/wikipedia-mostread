import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart';
import 'package:intl/intl.dart';
import 'package:logging/logging.dart';

import 'models/article.dart';
import '../async_rate_limiter/async_rate_limiter.dart';
import '../http_client/http_client.dart'
    if (dart.library.js_interop) '../http_client/http_client_web.dart'
    as http_client;
import 'wiki_api_exceptions.dart';

final log = Logger('wiki_api');

typedef WikiAPIErrorRecord = ({String url, String message});

enum WikiAPIResponseType {
  featuredContent(version: 1);

  const WikiAPIResponseType({
    required this.version,
  });

  final int version;

  String get name {
    switch (this) {
      case WikiAPIResponseType.featuredContent:
        return "featuredContent";
    }
  }
}

class WikiAPIUrl {
  final Uri uri;

  final WikiAPIResponseType type;

  const WikiAPIUrl(this.uri, this.type);

  String get cacheKey => "${uri.toString()}|${type.name}|${type.version}";

  bool get isValid => !uri.hasEmptyPath;
}

class WikiAPIResponse {
  final WikiAPIUrl url;

  final String processedContent;

  final Exception? exception;

  const WikiAPIResponse._internal(
      this.url, this.processedContent, this.exception);

  factory WikiAPIResponse.fromContent(String rawContent, WikiAPIUrl url) {
    final processedContent =
        WikiAPIResponse.processContent(rawContent, url.type);
    if (processedContent != null) {
      return WikiAPIResponse._internal(url, processedContent, null);
    } else {
      return WikiAPIResponse.fromException(
          url, WikipediaContentProcessingError());
    }
  }

  factory WikiAPIResponse.fromCache(WikiAPIUrl url, String processedContent) {
    return WikiAPIResponse._internal(url, processedContent, null);
  }

  factory WikiAPIResponse.fromException(WikiAPIUrl url, Exception e) {
    return WikiAPIResponse._internal(url, "", e);
  }

  static String? processContent(String rawContent, WikiAPIResponseType type) {
    switch (type) {
      case WikiAPIResponseType.featuredContent:
        return processFeaturedContent(rawContent);
      default:
        return null;
    }
  }

  /// Extract most read articles details from the Feed API Featured Content.
  /// e.g. `['{"tfa": ..., "mostread": ...', ...]`
  static String? processFeaturedContent(String rawContent) {
    late final Map<String, dynamic> jsonContent;
    try {
      jsonContent = jsonDecode(rawContent);
    } on Exception {
      log.severe("Invalid featured content JSON response: $rawContent");
      return null;
    }

    // "mostread.articles" might not be present if the requested date was today (still measuring views).
    if (!jsonContent.containsKey("mostread")) {
      return null;
    }

    try {
      final List<Article> articles = [];
      for (final jsonArticle in jsonContent["mostread"]["articles"]) {
        final List<ArticleViewHistoryRecord> viewHistory = [];
        for (final viewStats in jsonArticle["view_history"]) {
          viewHistory.add((
            // ISO 8601 Date format
            date: viewStats["date"].substring(0, 10),
            views: viewStats["views"],
          ));
        }
        // We could add more article details like "thumbnail".
        articles.add(Article(
            pageid: jsonArticle["pageid"],
            pageUrl: Uri.parse(jsonArticle["content_urls"]["desktop"]["page"]),
            title: jsonArticle["title"],
            // 🚨 Description might be null.
            description: jsonArticle["description"] ?? "",
            totalViews: jsonArticle["views"],
            viewHistory: viewHistory));
      }

      return jsonEncode({
        // ISO 8601 Date format
        "mostReadDate": jsonContent["mostread"]["date"].substring(0, 10),
        "articles": articles.map((entry) => Article.toJson(entry)).toList()
      });
    } on Exception {
      return null;
    }
  }

  bool get isValid =>
      exception == null && url.isValid && processedContent.isNotEmpty;
}

/// This abstract class acts as an interface to the caching layer,
/// which can be implemented in anything like a local dictionary or database.
///
///     Note:
///         We could also implement a `multi_get` function to offer a group fetch if the
///         caching layer has this capability.
abstract class WikiCache {
  WikiAPIResponse? get(WikiAPIUrl url);

  void put(WikiAPIResponse resp);
}

class WikiAPI {
  static const maxRequestsPerSec = 100; // Wikipedia API Rate Limit

  static const maxResponseResults = 5000;

  static const processedContentVersion = "1.0";

  final WikiCache? optionalCache;

  WikiAPI({this.optionalCache});

  WikiAPIResponse? _tryCacheGet(WikiAPIUrl url) {
    final cachedResponse = optionalCache?.get(url);
    if (cachedResponse != null) {
      log.info("CACHE HIT: ${url.cacheKey}");
    }
    return cachedResponse;
  }

  void _tryCachePut(WikiAPIResponse resp) {
    // Validate response eligibility for caching:
    // e.g. Cache Featured Content response only if mostread articles object is present.
    if (resp.isValid && optionalCache != null) {
      log.info("CACHE PUT: ${resp.url.cacheKey}");
      optionalCache?.put(resp);
    }
  }

  /// Fetches the most read articles from Wikipedia by supported language code and date range.
  ///
  ///       This function fetches data concurrently from Wikipedia's Feed API Featured Content for each day
  ///       on the specified range. The Feed API returns the top 50 featured articles (sometimes less as it filters
  ///       out pages irrelevant articles like Wikipedia's homepage). The Feed API was elected over the REST API
  ///       due to its filtering capabilities and focus on top 50 articles instead of top 1000.
  ///
  ///       Args:
  ///           langCode: Wikipedia language code
  ///           start: Start day to retrieve from. Format: YYYY-MM-DD
  ///           end: Last day (inclusive interval). Format: YYYY-MM-DD
  ///
  ///       Returns:
  ///           Sorted (descending) list of most read articles with total views and views history by date,
  ///           and errors if any occurred for a URL.
  ///               ```
  ///               e.g. {
  ///                   data: [{page: 'https://en.wikipedia...', total_views: 9000, view_history: [{date: '2020-12-30', views: 4500}], ...],
  ///                   errors: [{url: 'https://en.wikipedia...', message: 'Error connecting...'}, ...]
  ///               }
  ///               ```
  ///
  ///       Raises:
  ///           InvalidStartDateError: If `start` string date is not formatted correctly.
  ///           InvalidEndDateError: If `end` string date is not formatted correctly.
  ///           InvalidDateRangeError: If `end` date is before `start` date.
  ///           InvalidLanguageCodeError: If language code contains invalid characters.
  ///
  Future<(List<Article>, List<WikiAPIErrorRecord>)> fetchMostReadArticles(
      String langCode, String start, String end,
      {int resultsLimit = maxResponseResults}) async {
    final (startDate, endDate) = _parseFormattedDateRange(start, end);

    // 🚨 Counterintuitively the Feed API Featured Content needs to be queried one day in the future.
    // to return the wanted date's most read articles.
    final shiftedStartDate = startDate.add(const Duration(days: 1));
    final shiftedEndDate = endDate.add(const Duration(days: 1));

    final apiURLs = _buildFeedApiFeaturedContentUrls(
        langCode, shiftedStartDate, shiftedEndDate);

    final (missedURLs, responsesFromCacheHits) =
        _fetchProcessedContentFromCache(apiURLs);

    final responsesFromMissedURLs =
        await _fetchFeedApiFeaturedContentResponses(missedURLs);

    final List<WikiAPIErrorRecord> formattedErrorResponses = [];
    final List<WikiAPIResponse> successfulResponses = [];
    for (final resp in responsesFromCacheHits + responsesFromMissedURLs) {
      if (!resp.isValid) {
        // Invalid API response
        formattedErrorResponses.add(_formatWikiApiError(
            resp.url,
            switch (resp.exception) {
              WikiAPIError e => e.message,
              _ => null
            }));
      } else {
        // Successful API response
        successfulResponses.add(resp);
      }
    }

    final mostReadArticles =
        _reduceAndSortFeaturedContentMostReadArticles(successfulResponses);

    // Max response results reached message
    if (mostReadArticles.length > resultsLimit) {
      final message =
          "Limited response to $resultsLimit out of ${mostReadArticles.length} results.";
      formattedErrorResponses.insert(0, _formatWikiApiError(null, message));
      mostReadArticles.removeRange(resultsLimit, mostReadArticles.length);
    }

    return (mostReadArticles, formattedErrorResponses);
  }

  WikiAPIErrorRecord _formatWikiApiError(WikiAPIUrl? url, String? message) {
    return (
      url: url?.uri.toString() ?? "",
      message: message ?? WikipediaResponseError().message
    );
  }

  /// Reduces and sorts (DESC) most read articles total views from Wikipedia's Feed API Featured Content responses.
  ///
  ///    Args:
  ///        featuredContentResponses: List of Feed API Featured Content responses.
  ///            e.g. `['{"tfa": ..., "mostread": ...', ...]`
  ///
  ///    Returns:
  ///        Sorted list of most read articles with total views and views history by date.
  ///            e.g. `[{pageUrl: 'https://en.wikipedia...', totalViews: 9000, viewHistory: [{date: '2020-12-30', views: 4500}], ...]`
  ///            🚨 Note that views_history only contains views for days where the article was featured in the day's top 50.
  ///
  ///    Raises:
  ///        WikipediaContentProcessingError: If there's a JSON decoding or content integrity errors in `featuredContentResponses`.
  ///
  List<Article> _reduceAndSortFeaturedContentMostReadArticles(
      List<WikiAPIResponse> featuredContentResponses) {
    final Map<int, Article> articlesStats = {};
    final Map<int, Set<ArticleViewHistoryRecord>> articlesViewHistory = {};

    for (final resp in featuredContentResponses) {
      assert(resp.isValid);
      late final Map<String, dynamic> jsonContent;
      try {
        jsonContent = jsonDecode(resp.processedContent);
      } on Exception {
        log.severe(
            "Invalid featured content JSON response: ${resp.processedContent}");
        throw WikipediaContentProcessingError();
      }

      for (final jsonArticle in jsonContent["articles"]) {
        final Article article = Article.fromJson(jsonArticle);

        // Prepare new article stats slot for aggregation.
        if (!articlesStats.containsKey(article.pageid)) {
          articlesStats[article.pageid] = article;
          articlesViewHistory[article.pageid] = {};
        } else {
          // Aggregate total views through different days.
          articlesStats[article.pageid]!.totalViews += article.totalViews;
        }

        // Maintain unique articles views history entries.
        for (final entry in article.viewHistory) {
          articlesViewHistory[article.pageid]!.add(entry);
        }
      }
    }

    for (final mapEntry in articlesViewHistory.entries.toList()) {
      final pageid = mapEntry.key;
      final viewHistory = mapEntry.value.toList();
      viewHistory.sort((a, b) => a.date.compareTo(b.date));
      articlesStats[pageid]!.viewHistory = viewHistory;
    }

    // Extract and sort article URLs by total views in descending order.
    final List<Article> sortedArticles = articlesStats.values.toList();
    sortedArticles.sort((a, b) => b.totalViews.compareTo(a.totalViews));

    return sortedArticles;
  }

  (List<WikiAPIUrl>, List<WikiAPIResponse>) _fetchProcessedContentFromCache(
      List<WikiAPIUrl> apiURLs) {
    List<WikiAPIResponse> cacheHits = [];
    List<WikiAPIUrl> missedURLs = [];

    for (final url in apiURLs) {
      final cachedResponse = _tryCacheGet(url);
      if (cachedResponse != null) {
        cacheHits.add(cachedResponse);
      } else {
        missedURLs.add(url);
      }
    }
    return (missedURLs, cacheHits);
  }

  /// Gets a list of responses from Wikipedia's Feed API Featured Content from a URL list.
  ///
  ///    This function runs concurrent API requests taking advantage of HTTP/2
  ///    and throttles `maxRequestsPerSec` active requests per second.
  ///
  ///    Args:
  ///        langCode: Wikipedia API URLs.
  ///
  ///    Returns:
  ///        List of Feed API Featured Content responses.
  ///          e.g. `[WikiAPIResponse(url, response, exception), ... ]`
  ///
  Future<List<WikiAPIResponse>> _fetchFeedApiFeaturedContentResponses(
      List<WikiAPIUrl> urls) async {
    final Client client = http_client.httpClient();
    final fetchTasks = [
      for (final url in urls) () => _fetchWikiApiResponse(url, client)
    ];
    final results = await runRateLimitedTasks(fetchTasks,
        maxTasksPerSecond: WikiAPI.maxRequestsPerSec);
    client.close();

    // Guarantee non-nulls;
    List<WikiAPIResponse> responses = [];
    for (final (index, resp) in results.indexed) {
      if (resp == null) {
        responses.add(WikiAPIResponse.fromException(
            urls[index], WikipediaResponseError()));
      } else {
        responses.add(resp);
      }
    }
    return responses;
  }

  Future<WikiAPIResponse> _fetchWikiApiResponse(
      WikiAPIUrl url, Client client) async {
    try {
      log.info("Fetching: ${url.uri.toString()}");

      final response = await client.send(Request('GET', url.uri));

      if (response.statusCode == 200) {
        final content = await utf8.decodeStream(response.stream);
        final resp = WikiAPIResponse.fromContent(content, url);
        _tryCachePut(resp);
        return resp;
      } else {
        log.severe(
            "Wikipedia API unexpected response status code for request: ${url.uri.toString()}");
        return WikiAPIResponse.fromException(url, WikipediaResponseError());
      }
    } on ClientException catch (e) {
      log.severe(
          "Wikipedia API Connection Error for request: ${url.uri.toString()}. Error: ${e.message}");
      return WikiAPIResponse.fromException(url, WikipediaConnectionError());
    } on Exception catch (e) {
      log.severe(
          "Wikipedia API Error for request: ${url.uri.toString()}. Error: $e");
      return WikiAPIResponse.fromException(url, e);
    } catch (e) {
      log.severe(
          "Unexpected error while fetching and processing request: ${url.uri.toString()}. Error: $e");
      return WikiAPIResponse.fromException(
          url, WikipediaContentProcessingError());
    }
  }

  /// Builds a date range list of Wikipedia's Feed API Featured Content URLs.
  ///
  /// Args:
  ///     langCode: Wikipedia language code.
  ///     startDate: Start day of range.
  ///     endDate: Last day of range (inclusive).
  ///
  /// Returns:
  ///     List of API URLs.
  ///         e.g. `[https://en.wikipedia.org/api/rest_v1/feed/featured/2024/02/19, ...]`
  ///
  /// Raises:
  ///     InvalidLanguageCodeError: If language code contains invalid characters.
  ///
  List<WikiAPIUrl> _buildFeedApiFeaturedContentUrls(
      String langCode, DateTime startDate, DateTime endDate) {
    List<WikiAPIUrl> urls = [];

    if (!_validateLanguageCode(langCode)) {
      throw InvalidLanguageCodeError();
    }

    final dateFormatter = DateFormat("y/MM/dd", "en_US");
    var curDay = startDate;
    while (!curDay.isAfter(endDate)) {
      final formattedDate = dateFormatter.format(curDay);
      urls.add(WikiAPIUrl(
          Uri.https("$langCode.wikipedia.org",
              "/api/rest_v1/feed/featured/$formattedDate"),
          WikiAPIResponseType.featuredContent));
      curDay = curDay.add(const Duration(days: 1));
    }
    return urls;
  }

  ///  Checks that a language code only contains letters, numbers or dashes.
  ///
  ///  See Wikipedia languages here: https://wikistats.wmcloud.org/display.php?t=wp
  ///
  bool _validateLanguageCode(String langCode) {
    final pattern = RegExp(r"^[a-zA-Z0-9-]+$");
    return pattern.hasMatch(langCode);
  }

  /// Parses YYYYMMDD formatted string arguments into datetime objects.
  ///
  ///       Returns:
  ///           Tuple (`start`, `end`) as datetime values.
  ///
  ///       Raises:
  ///           InvalidStartDateError: If `start` string date is not formatted correctly.
  ///           InvalidEndDateError: If `end` string date is not formatted correctly.
  ///           InvalidDateRangeError: If `end` date is before `start` date.
  ///
  (DateTime, DateTime) _parseFormattedDateRange(String start, String end) {
    final dateFormatter = DateFormat("y-M-d", "en_US");

    late DateTime startDate;
    late DateTime endDate;

    try {
      startDate = dateFormatter.parseStrict(start);
    } on FormatException {
      throw InvalidStartDateError();
    }

    try {
      endDate = dateFormatter.parseStrict(end);
    } on FormatException {
      throw InvalidEndDateError();
    }

    if (startDate.isAfter(endDate)) {
      throw InvalidDateRangeError();
    }

    return (startDate, endDate);
  }
}

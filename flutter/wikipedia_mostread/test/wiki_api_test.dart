import 'dart:convert';

import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:logging/logging.dart';
import 'package:test/test.dart';

import 'package:wikipedia_mostread/shared/wiki_api/models/article.dart';
import 'package:wikipedia_mostread/shared/wiki_api/wiki_api.dart';
import 'package:wikipedia_mostread/shared/wiki_api/wiki_api_exceptions.dart';

import 'expected_results_wiki_api.dart' as expected_results;

final log = Logger('wiki_api_test');

/// This is a subclass of WikiCache used to store WikiAPI responses in a dictionary
/// to ease testing validation.
///
class TestCache extends WikiCache {
  final Map<String, String> _cache = {};

  @override
  WikiAPIResponse? get(WikiAPIUrl url) {
    final cachedContent = _cache[url.cacheKey];
    if (cachedContent != null) {
      return WikiAPIResponse.fromCache(url, cachedContent);
    }
    return null;
  }

  @override
  void put(WikiAPIResponse resp) {
    assert(resp.isValid);
    _cache[resp.url.cacheKey] = resp.processedContent;
  }
}

void main() {
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    if (kDebugMode) {
      print('${record.level.name}: ${record.time}: ${record.message}');
    }
  });

  late TestCache testCache;
  late WikiAPI wikiAPI;

  setUp(() {
    testCache = TestCache();
    wikiAPI = WikiAPI(optionalCache: testCache);
  });

  test('fetchMostReadArticles() success', () async {
    final List<
        ({
          String langCode,
          String start,
          String end,
          String description,
          List<Article> expectedArticles,
          List<WikiAPIErrorRecord> expectedErrors,
          int? limitResults,
        })> cases = [
      (
        langCode: "es",
        start: "2024-02-19",
        end: "2024-02-19",
        description: "Test 1-day range Spanish Wikipedia",
        expectedArticles: expected_results.expectedMostRead_es_20240219,
        expectedErrors: [],
        limitResults: null,
      ),
      (
        langCode: "it",
        start: "2024-02-19",
        end: "2024-02-20",
        description: "Test 2-day range Italian Wikipedia",
        expectedArticles:
            expected_results.expectedMostRead_it_20240219_20240220,
        expectedErrors: [
          (url: "", message: "Limited response to 5 out of 72 results.")
        ],
        limitResults: 5,
      ),
    ];

    for (final c in cases) {
      late final (List<Article>, List<WikiAPIErrorRecord>) results;
      if (c.limitResults != null) {
        results = await wikiAPI.fetchMostReadArticles(
            c.langCode, c.start, c.end,
            resultsLimit: c.limitResults!);
      } else {
        results =
            await wikiAPI.fetchMostReadArticles(c.langCode, c.start, c.end);
      }
      final (articles, errors) = results;
      expect(articles, equals(c.expectedArticles), reason: c.description);
      expect(errors, equals(c.expectedErrors), reason: c.description);
    }

    // Cache validation
    const expectedCacheKeys = {
      "https://es.wikipedia.org/api/rest_v1/feed/featured/2024/02/20|featuredContent|1",
      "https://it.wikipedia.org/api/rest_v1/feed/featured/2024/02/20|featuredContent|1",
      "https://it.wikipedia.org/api/rest_v1/feed/featured/2024/02/21|featuredContent|1",
    };
    expect(testCache._cache.keys.toSet(), equals(expectedCacheKeys));

    // Cache content
    final cachedProcessedContent = testCache._cache[
            "https://es.wikipedia.org/api/rest_v1/feed/featured/2024/02/20|featuredContent|1"] ??
        "";
    final cachedJson = jsonDecode(cachedProcessedContent);
    expect(cachedJson["mostReadDate"], equals("2024-02-19"));
    expect(cachedJson["articles"].length, equals(45));

    // Test results after cached response hit.
    final (cachedResultsArticles, cachedResultsErrors) = await wikiAPI
        .fetchMostReadArticles(cases[0].langCode, cases[0].start, cases[0].end);
    expect(cachedResultsArticles, equals(cases[0].expectedArticles));
    expect(cachedResultsErrors, equals(cases[0].expectedErrors));
  });

  test('fetchMostReadArticles() no cache layer success', () async {
    final List<Article> expectedArticles =
        expected_results.expectedMostRead_es_20240219;
    final List<WikiAPIErrorRecord> expectedErrors = [];

    final noCacheWikiApi = WikiAPI();
    final (articles, errors) = await noCacheWikiApi.fetchMostReadArticles(
        "es", "2024-02-19", "2024-02-19");
    expect(articles, equals(expectedArticles));
    expect(errors, equals(expectedErrors));
  });

  test('fetchMostReadArticles() exceptions', () async {
    final List<
        ({
          String langCode,
          String start,
          String end,
          TypeMatcher expectedException,
        })> cases = [
      (
        langCode: "en",
        start: "2024-19-02",
        end: "2024-02-19",
        expectedException: isA<InvalidStartDateError>()
      ),
      (
        langCode: "es",
        start: "2024-02-19",
        end: "2024-19-02",
        expectedException: isA<InvalidEndDateError>()
      ),
      (
        langCode: "es",
        start: "2024-02-20",
        end: "2024-02-19",
        expectedException: isA<InvalidDateRangeError>()
      ),
      (
        langCode: "hax0r.com/pwned",
        start: "2024-02-19",
        end: "2024-02-19",
        expectedException: isA<InvalidLanguageCodeError>(),
      ),
    ];

    for (final c in cases) {
      expect(wikiAPI.fetchMostReadArticles(c.langCode, c.start, c.end),
          throwsA(c.expectedException));
    }

    // Validate cache remained empty
    expect(testCache._cache, isEmpty);
  });

  test('fetchMostReadArticles() response errors', () async {
    final tomorrow = DateTime.now().add(const Duration(days: 1));
    final tomorrowShifted = tomorrow.add(const Duration(days: 1));

    final List<
        ({
          String langCode,
          String start,
          String end,
          String expectedErrorUrl,
          String expectedErrorMessage,
        })> cases = [
      // Tomorrow's page views do not exist yet, however API returns 200 response for other scheduled Featured Content.
      (
        langCode: "en",
        start: tomorrow.toString().substring(0, 10),
        end: tomorrow.toString().substring(0, 10),
        expectedErrorUrl:
            "https://en.wikipedia.org/api/rest_v1/feed/featured/${tomorrowShifted.toString().substring(0, 10).replaceAll("-", "/")}",
        expectedErrorMessage: WikipediaContentProcessingError().message
      ),
      // Host fails for non-existent language codes.
      (
        langCode: "valyrian",
        start: "2024-02-19",
        end: "2024-02-19",
        expectedErrorUrl:
            "https://valyrian.wikipedia.org/api/rest_v1/feed/featured/2024/02/20",
        expectedErrorMessage: WikipediaConnectionError().message,
      ),
      // A thousand years in the future response an error response.
      (
        langCode: "en",
        start: "3024-02-19",
        end: "3024-02-19",
        expectedErrorUrl:
            "https://en.wikipedia.org/api/rest_v1/feed/featured/3024/02/20",
        expectedErrorMessage: WikipediaResponseError().message,
      ),
    ];

    final List<Article> expectedArticles = [];
    for (final c in cases) {
      final List<WikiAPIErrorRecord> expectedErrors = [
        (
          url: c.expectedErrorUrl,
          message: c.expectedErrorMessage,
        ),
      ];
      final (articles, errors) =
          await wikiAPI.fetchMostReadArticles(c.langCode, c.start, c.end);
      expect(articles, equals(expectedArticles));
      expect(errors, equals(expectedErrors));
    }

    // Validate cache remained empty
    expect(testCache._cache, isEmpty);
  });
}

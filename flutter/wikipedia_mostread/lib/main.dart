import 'dart:async' show TimeoutException;

import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:logging/logging.dart';
import 'package:provider/provider.dart';
import 'package:wikipedia_mostread/shared/wiki_api/models/language.dart';
import 'package:wikipedia_mostread/text_date_picker.dart';

import 'article_list.dart';
import 'language_dropdown.dart';
import 'partial_errors.dart';
import 'shared/wiki_api/wiki_api_exceptions.dart';
import 'shared/wiki_api/models/article.dart';
import 'shared/wiki_api/wiki_api.dart';
import 'shared/wiki_api/wiki_cache.dart'
    if (dart.library.js_interop) 'shared/wiki_api/wiki_cache_web.dart'
    as wiki_cache;

void main() {
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    if (kDebugMode) {
      print('${record.level.name}: ${record.time}: ${record.message}');
    }
  });

  runApp(Provider<WikiAPI>(
      create: (_) => WikiAPI(optionalCache: wiki_cache.wikiCache()),
      child: const WikipediaMostReadApp()));
}

class WikipediaMostReadApp extends StatelessWidget {
  static const fetchTimeoutSeconds = 60;

  static const title = "Wikipedia - Most Read Articles";

  const WikipediaMostReadApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: WikipediaMostReadApp.title,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.grey),
        useMaterial3: true,
      ),
      home: const HomePage(title: WikipediaMostReadApp.title),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.title});

  final String title;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late WikiAPI _wikiAPI;
  bool _isLoading = false;
  String? _fetchSevereError;
  List<Article>? _articles;
  List<WikiAPIErrorRecord> _partialErrors = [];
  WikiLanguage _language = WikiLanguage.defaultLanguageCode;
  DateTime _startDate = DateTime.now().subtract(const Duration(days: 1));
  DateTime _endDate = DateTime.now().subtract(const Duration(days: 1));

  @override
  void initState() {
    super.initState();
    _wikiAPI = context.read<WikiAPI>();
  }

  void updateLanguage(WikiLanguage selectedLanguage) {
    setState(() {
      _language = selectedLanguage;
    });
  }

  void updateStartDate(DateTime date) {
    setState(() {
      _startDate = date;
    });
  }

  void updateEndDate(DateTime date) {
    setState(() {
      _endDate = date;
    });
  }

  void _fetchMostReadArticles() async {
    if (_isLoading) return;

    setState(() {
      _isLoading = true;
      _fetchSevereError = null;
    });

    Future(() async {
      (List<Article>, List<WikiAPIErrorRecord>)? fetchResults;
      String? fetchError;

      try {
        // TODO: Look into terminating rate limited task on timeout.
        fetchResults = await _wikiAPI
            .fetchMostReadArticles(
                _language.code,
                _startDate.toString().substring(0, 10),
                _endDate.toString().substring(0, 10))
            .timeout(const Duration(
                seconds: WikipediaMostReadApp.fetchTimeoutSeconds));
      } on TimeoutException {
        fetchError =
            "The server took too long to complete the task. Please try again.";
      } on WikiAPIError catch (e) {
        fetchError = e.message;
      } catch (e) {
        fetchError = e.toString();
      }

      setState(() {
        _isLoading = false;
        _fetchSevereError = fetchError;
        _articles = fetchResults?.$1 ?? [];
        _partialErrors = fetchResults?.$2 ?? [];
      });
    });
  }

  final fetchCallToActionMessage = const Center(
    child: Text(
      "Fetch Wikipedia's most read articles within a date range.",
      style: TextStyle(fontSize: 18),
    ),
  );

  final loadingMessage = const Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        CircularProgressIndicator(
          color: Colors.lightBlue,
          strokeWidth: 3,
        ),
        SizedBox(height: 16),
        Text(
          "Fetching most read articles...",
          style: TextStyle(fontSize: 18),
        ),
        SizedBox(height: 8),
        Text(
          "This might take while for large date ranges.",
        ),
      ],
    ),
  );

  final emptyResultsMessage = const Center(
    child: Text(
      "No results found during this date range.",
      style: TextStyle(fontSize: 18),
    ),
  );

  Widget renderSevereErrorMessage() => Center(
        child: Text(
          "❌ ${_fetchSevereError ?? ''}",
          style: const TextStyle(color: Colors.redAccent, fontSize: 18),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final fetchResults = _articles == null
        ? fetchCallToActionMessage
        : _articles!.isNotEmpty
            ? ArticleList(_articles!)
            : emptyResultsMessage;

    final expandedResults =
        _fetchSevereError == null ? fetchResults : renderSevereErrorMessage();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Column(
        children: [
          const SizedBox(height: 10),
          Expanded(
            flex: 0,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Language:",
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(width: 10),
                  LanguageDropdown(
                      language: _language, onChanged: updateLanguage),
                  const SizedBox(width: 10),
                  TextDatePicker(
                    title: "Start",
                    date: _startDate,
                    onChanged: updateStartDate,
                  ),
                  const SizedBox(width: 10),
                  TextDatePicker(
                    title: "End",
                    date: _endDate,
                    onChanged: updateEndDate,
                  ),
                  const SizedBox(width: 10),
                  FilledButton(
                    onPressed: _isLoading ? null : _fetchMostReadArticles,
                    child: const Text("Fetch"),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          PartialErrors(partialErrors: _partialErrors),
          Expanded(
              flex: 1, child: _isLoading ? loadingMessage : expandedResults),
        ],
      ),
    );
  }
}

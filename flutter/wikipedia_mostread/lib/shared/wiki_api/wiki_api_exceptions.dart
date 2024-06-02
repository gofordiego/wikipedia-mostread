/// Base class for all exceptions from this module.
class WikiAPIError implements Exception {
  String get message => _message;
  final String _message;

  WikiAPIError(this._message);
}

class InvalidArticlePageError extends WikiAPIError {
  InvalidArticlePageError() : super("Invalid Wikipedia article page.");
}

class InvalidLanguageCodeError extends WikiAPIError {
  InvalidLanguageCodeError() : super("Invalid Wikipedia language code.");
}

class InvalidStartDateError extends WikiAPIError {
  InvalidStartDateError() : super("Invalid start date.");
}

class InvalidEndDateError extends WikiAPIError {
  InvalidEndDateError() : super("Invalid end date.");
}

class InvalidDateRangeError extends WikiAPIError {
  InvalidDateRangeError()
      : super("Invalid date range, start date should be before the end date.");
}

class WikipediaConnectionError extends WikiAPIError {
  WikipediaConnectionError()
      : super("Error connecting to the Wikipedia server.");
}

class WikipediaResponseError extends WikiAPIError {
  /// Note: We could create a secondary error to be more explicit about being rate limited,
  /// in addition to receiving a non-200 OK response.

  WikipediaResponseError()
      : super(
            "Wikipedia server returned an unexpected response, could be rate limited.");
}

class WikipediaContentProcessingError extends WikiAPIError {
  WikipediaContentProcessingError()
      : super(
            "Unexpected error while processing the content of a response from the Wikipedia API.");
}

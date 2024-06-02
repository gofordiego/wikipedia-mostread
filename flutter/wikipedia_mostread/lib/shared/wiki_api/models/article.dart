import 'package:flutter/foundation.dart' show listEquals;

typedef ArticleViewHistoryRecord = ({String date, int views});

class Article {
  final int pageid;
  final Uri pageUrl;
  final String title;
  final String description;
  // Used to aggregate stats for different dates.
  int totalViews;
  List<ArticleViewHistoryRecord> viewHistory;
  // Example:
  // {
  //   pageid: 736,
  //   pageUrl: https://en.wikipedia.org/wiki/Albert_Einstein,
  //   title: Albert_Einstein,
  //   description: German-born physicist (1879–1955),
  //   totalViews: <int>,
  //   viewHistory: [{date: "YYYY-MM-DD", views: <int>}, ... ]
  // }
  bool isExpanded;

  Article(
      {required this.pageid,
      required this.pageUrl,
      required this.title,
      required this.description,
      required this.totalViews,
      required this.viewHistory,
      this.isExpanded = false});

  Article.fromJson(Map<String, dynamic> json)
      : pageid = json['pageid'],
        pageUrl = Uri.parse(json['pageUrl']),
        title = json['title'],
        description = json['description'],
        totalViews = json['totalViews'],
        viewHistory = [
          for (final entry in json['viewHistory'])
            (date: entry["date"], views: entry["views"])
        ],
        isExpanded = false;

  static Map<String, dynamic> toJson(Article article) => {
        "pageid": article.pageid,
        "pageUrl": article.pageUrl.toString(),
        "title": article.title,
        "description": article.description,
        "totalViews": article.totalViews,
        "viewHistory": article.viewHistory
            .map((entry) => {"date": entry.date, "views": entry.views})
            .toList()
      };

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is Article &&
        other.pageid == pageid &&
        other.pageUrl == pageUrl &&
        other.title == title &&
        // 🚨 Descriptions containing non-breaking spaces (U+00A0) were messing up unit testing comparisons.
        //    So opted to replace for standard space (U+0020).
        other.description.replaceAll(RegExp(r'\s'), " ") ==
            description.replaceAll(RegExp(r'\s'), " ") &&
        other.totalViews == totalViews &&
        listEquals(other.viewHistory, viewHistory);
  }

  @override
  int get hashCode =>
      Object.hash(pageid, pageUrl, title, description, totalViews, viewHistory);

  @override
  String toString() {
    return Article.toJson(this).toString();
  }
}

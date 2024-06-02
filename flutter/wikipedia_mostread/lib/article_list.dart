import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import 'package:syncfusion_flutter_charts/sparkcharts.dart';
import 'package:url_launcher/url_launcher.dart';

import 'shared/wiki_api/models/article.dart';

class ArticleList extends StatefulWidget {
  final List<Article> articles;

  const ArticleList(this.articles, {super.key});

  @override
  State<ArticleList> createState() => _ArticleListState();
}

class _ArticleListState extends State<ArticleList> {
  final _decimalFormatter = NumberFormat.decimalPatternDigits();
  late TooltipBehavior _tooltipBehavior;

  @override
  void initState() {
    _tooltipBehavior = TooltipBehavior(enable: true, header: "Views");
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Container(
        child: _buildPanel(),
      ),
    );
  }

  Widget _buildPanel() {
    return ExpansionPanelList(
      expansionCallback: (int index, bool isExpanded) {
        setState(() {
          widget.articles[index].isExpanded = isExpanded;
        });
      },
      children: widget.articles.asMap().entries.map<ExpansionPanel>((entry) {
        final int index = entry.key;
        final Article article = entry.value;
        return ExpansionPanel(
            canTapOnHeader: true,
            headerBuilder: (BuildContext context, bool isExpanded) {
              return CollapsedArticle(
                  article: article,
                  rank: index + 1,
                  decimalFormatter: _decimalFormatter);
            },
            body: ExpandedArticle(
                article: article,
                tooltipBehavior: _tooltipBehavior,
                decimalFormatter: _decimalFormatter),
            isExpanded: article.isExpanded);
      }).toList(),
    );
  }
}

class CollapsedArticle extends StatelessWidget {
  final Article article;
  final int rank;
  final NumberFormat decimalFormatter;

  const CollapsedArticle(
      {super.key,
      required this.article,
      required this.rank,
      required this.decimalFormatter});

  @override
  Widget build(BuildContext context) {
    final Widget? sparkLineChart = article.isExpanded
        ? null
        : SfSparkLineChart(
            axisLineWidth: 0,
            color: Colors.lightBlue,
            data: article.viewHistory
                .map((viewHistory) => viewHistory.views)
                .toList(),
          );
    final Widget trailingChart =
        SizedBox(height: 30, width: 120, child: sparkLineChart);

    return ListTile(
      leading: Text("$rank.",
          style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: Theme.of(context).textTheme.bodyLarge?.fontSize)),
      title: Text(article.title),
      subtitle: RichText(
        text: TextSpan(
          children: <TextSpan>[
            TextSpan(text: "${article.description}\n"),
            TextSpan(
                text:
                    "${decimalFormatter.format(article.totalViews)} total views",
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      ),
      trailing: trailingChart,
    );
  }
}

class ExpandedArticle extends StatelessWidget {
  final Article article;
  final TooltipBehavior tooltipBehavior;
  final NumberFormat decimalFormatter;

  const ExpandedArticle(
      {super.key,
      required this.article,
      required this.tooltipBehavior,
      required this.decimalFormatter});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          InkWell(
            child: Text(
              "🔗 ${article.pageUrl.toString()}",
              style: TextStyle(
                  color: Colors.blueAccent,
                  fontSize: Theme.of(context).textTheme.titleMedium?.fontSize),
            ),
            onTap: () =>
                launchUrl(article.pageUrl, webOnlyWindowName: "_blank"),
          ),
          SizedBox(
            height: 300,
            width: 500,
            child: SfCartesianChart(
              primaryXAxis: const CategoryAxis(
                interactiveTooltip: InteractiveTooltip(enable: true),
              ),
              primaryYAxis: NumericAxis(numberFormat: decimalFormatter),
              tooltipBehavior: tooltipBehavior,
              series: <LineSeries<ArticleViewHistoryRecord, String>>[
                LineSeries<ArticleViewHistoryRecord, String>(
                    animationDuration: 0,
                    color: Colors.lightBlue,
                    dataSource: article.viewHistory,
                    xValueMapper: (ArticleViewHistoryRecord viewHistory, _) =>
                        viewHistory.date,
                    yValueMapper: (ArticleViewHistoryRecord viewHistory, _) =>
                        viewHistory.views)
              ],
            ),
          ),
        ],
      ),
    ]);
  }
}

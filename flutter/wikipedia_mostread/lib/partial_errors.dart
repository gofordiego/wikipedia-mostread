import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import "shared/wiki_api/wiki_api.dart" show WikiAPIErrorRecord;

class PartialErrors extends StatelessWidget {
  final List<WikiAPIErrorRecord> partialErrors;

  const PartialErrors({super.key, required this.partialErrors});

  final titleLabel = const Text(
    "⚠️ Partial Wikipedia API Errors",
    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
  );

  Widget renderPartialError(WikiAPIErrorRecord error) {
    final uri = Uri.tryParse(error.url);
    late final Widget item;

    // Apparently empty string "" still parses correctly.
    if (error.url.isNotEmpty && uri != null) {
      item = InkWell(
        child: RichText(
          text: TextSpan(
            children: <TextSpan>[
              const TextSpan(text: "• "),
              TextSpan(
                  text: uri.toString(),
                  style: const TextStyle(color: Colors.redAccent)),
              TextSpan(text: " – ${error.message}")
            ],
          ),
        ),
        onTap: () => launchUrl(uri, webOnlyWindowName: "_blank"),
      );
    } else {
      item = Text("• ${error.message}");
    }

    return item;
  }

  @override
  Widget build(BuildContext context) {
    if (partialErrors.isEmpty) {
      return const SizedBox(height: 0);
    }
    final List<Widget> errors = [titleLabel];

    errors.addAll(partialErrors.map(renderPartialError).toList());

    return Expanded(
        flex: 0,
        child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: errors)));
  }
}

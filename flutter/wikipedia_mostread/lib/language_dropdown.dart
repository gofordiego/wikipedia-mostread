import 'package:flutter/material.dart';

import 'shared/wiki_api/models/language.dart';

class LanguageDropdown extends StatelessWidget {
  final WikiLanguage language;
  final ValueChanged<WikiLanguage> onChanged;

  const LanguageDropdown(
      {required this.language, required this.onChanged, super.key});

  @override
  Widget build(BuildContext context) {
    return DropdownMenu<WikiLanguage>(
      initialSelection: language,
      onSelected: (WikiLanguage? value) {
        onChanged(value!);
      },
      dropdownMenuEntries: WikiLanguage.languages
          .map<DropdownMenuEntry<WikiLanguage>>((WikiLanguage selection) {
        return DropdownMenuEntry<WikiLanguage>(
            value: selection, label: selection.name);
      }).toList(),
    );
  }
}

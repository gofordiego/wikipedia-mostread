import 'package:flutter/material.dart';

class TextDatePicker extends StatelessWidget {
  final String title;
  final DateTime date;
  final ValueChanged<DateTime> onChanged;

  const TextDatePicker(
      {required this.title,
      required this.date,
      required this.onChanged,
      super.key});

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: () => selectDate(context),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
                text: "$title: ",
                style: const TextStyle(fontWeight: FontWeight.bold)),
            TextSpan(text: date.toString().substring(0, 10)),
          ],
        ),
      ),
    );
  }

  Future<void> selectDate(BuildContext context) async {
    DateTime? selected = await showDatePicker(
        context: context,
        firstDate: DateTime(2001),
        lastDate: DateTime.now().subtract(const Duration(days: 1)),
        currentDate: date);
    if (selected != null) {
      onChanged(selected);
    }
  }
}

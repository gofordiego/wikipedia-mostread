import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:logging/logging.dart';
import 'package:test/test.dart';

import 'package:wikipedia_mostread/shared/async_rate_limiter/async_rate_limiter.dart';

final log = Logger('async_rate_limiter_test');

class TestTaskException implements Exception {}

void main() {
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    if (kDebugMode) {
      print('${record.level.name}: ${record.time}: ${record.message}');
    }
  });

  /// Delays `number` seconds in returning the same argument
  Future<int> delayedNumber(int number, {bool raiseException = false}) async {
    log.info("Delay ($number secs). Started");

    if (raiseException) {
      throw TestTaskException();
    }

    for (var i = 0; i < number; i++) {
      // For testing purposes wait less than a second to make it to next scheduling cycle.
      await Future.delayed(const Duration(milliseconds: 950));
      log.info("Delay ($number secs). Passed ${i + 1} seconds");
    }

    log.info("Delay ($number secs). Completed");

    return number;
  }

  /// Wraps delayedNumber Future to prevent immediate execution.
  Future<int> Function() escapingTask(int number,
      {bool raiseException = false}) {
    return () => delayedNumber(number, raiseException: raiseException);
  }

  test('runRateLimitedTasks() success', () async {
    /*
     *  Note:
     *  Testing 'expected_time' in production CI might be flaky due to variable CPU load,
     *  here we mainly use it for illustrative debugging purposes
     *
     *  Case Example:
     *
     *      maxTasksPerSec=2
     *      tasks=[delayedNumber(1), delayedNumber(2), delayedNumber(3)]
     *
     *      expectedResults=[1, 2, 3]
     *      expectedTime=4  (1-second cycles)
     *
     *           -----------------------------------------
     *          | Cycle 1  | Cycle 2  | Cycle 3 | Cycle 4 |
     *          |----------|----------|---------|---------|
     *  Slot A: | delay(1) | delay(3) |   ...   |   ...   |
     *  Slot B: | delay(2) |   ...    |   Free  |   Free  |
     *           -----------------------------------------
     */
    final List<
        ({
          List<Future<int> Function()> tasks,
          int maxTasksPerSec,
          String description,
          List<int> expectedResults,
          int expectedTime,
        })> cases = [
      (
        tasks: [],
        maxTasksPerSec: 2,
        description: "0 running, 0 queued",
        expectedResults: [],
        expectedTime: 0
      ),
      (
        tasks: [escapingTask(3), escapingTask(2), escapingTask(1)],
        maxTasksPerSec: 1,
        description: "1 running, 2 queued",
        expectedResults: [3, 2, 1],
        expectedTime: 6
      ),
      (
        tasks: [escapingTask(1), escapingTask(2), escapingTask(3)],
        maxTasksPerSec: 2,
        description: "2 running, 1 queued",
        expectedResults: [1, 2, 3],
        expectedTime: 4
      ),
      (
        tasks: [escapingTask(1), escapingTask(2), escapingTask(3)],
        maxTasksPerSec: 3,
        description: "3 running, 0 queued",
        expectedResults: [1, 2, 3],
        expectedTime: 3
      ),
    ];

    const assertionTimeDelta = 0.5; // Seconds

    for (var c in cases) {
      final startTime = DateTime.now().millisecondsSinceEpoch;
      final results = await runRateLimitedTasks(c.tasks,
          maxTasksPerSecond: c.maxTasksPerSec);
      final totalTime =
          (DateTime.now().millisecondsSinceEpoch - startTime) / 1000;

      expect(results, equals(c.expectedResults), reason: c.description);

      // Asserting almost equal expected and got total run time.
      expect(totalTime, closeTo(c.expectedTime, assertionTimeDelta));
    }
  });

  test('runRateLimitedTasks() error', () async {
    final List<Future<int> Function()> tasks = [
      escapingTask(1),
      escapingTask(1, raiseException: true)
    ];
    const maxTasksPerSec = 2;

    expect(runRateLimitedTasks(tasks, maxTasksPerSecond: maxTasksPerSec),
        throwsA(isA<TestTaskException>()));
  });
}

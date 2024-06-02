import 'dart:async';
import 'dart:math' as math;

import 'package:logging/logging.dart';

final log = Logger('async_rate_limiter');

///  Rate limits a number of concurrent tasks per second.
///
///  Note:
///      The default 1-second rate limit window (delay per cycle) could be abstracted as an argument for greater extensibility.
///      Further failed task retry logic/exception handling could be implemented at the expense of added complexity.
///
///  Args:
///      tasks: List of async compute functions to run concurrently.
///      maxTasksPerSecond: Maximum tasks per second.
///
///  Returns:
///      List of tasks results.
///
///  Raises:
///      Exception: If a task fails, it bubbles up the exception, and cancels all running tasks.
///
Future<List<T?>> runRateLimitedTasks<T>(Iterable<Future<T> Function()> tasks,
    {int maxTasksPerSecond = 2}) async {
  // Sends complete signal when all tasks have been processed.
  var completer = Completer<List<T?>>.sync();

  // Collects the values. Set to null on error.
  var values = List<T?>.filled(tasks.length, null);

  // Total task processed/finished.
  var totalProcessed = 0;

  void handleValue(T value, int pos) {
    totalProcessed++;
    assert(values[pos] == null);
    values[pos] = value;

    if (!completer.isCompleted && totalProcessed == tasks.length) {
      completer.complete(values);
    }
  }

  void handleError(Object error) {
    if (!completer.isCompleted) {
      completer.completeError(error);
    }
  }

  if (tasks.isEmpty) {
    completer.complete(values);
    return completer.future;
  }

  var cycleCount = 0;
  var totalScheduled = 0;
  var runningTasks = <Future<T>>{};
  while (true) {
    // Total remaining futures to be scheduled
    final totalRemaining = tasks.length - totalScheduled;

    // Total slots available for the current cycle (rate limit per second)
    final totalSlotsAvailable = maxTasksPerSecond - runningTasks.length;

    // When remaining < total slots available, we won't need to rate limit anymore.
    final remainingToSchedule = math.min(totalSlotsAvailable, totalRemaining);

    // Schedule futures to start running concurrently in the task group.
    for (var i = 0; i < remainingToSchedule; i++) {
      final currentTask = tasks.elementAt(totalScheduled);
      Future<T> taskFuture = Future(() async {
        return await currentTask();
      });
      runningTasks.add(taskFuture);
      final pos = totalScheduled;
      taskFuture.whenComplete(() {
        // Runs before .then()
        runningTasks.remove(taskFuture);
      }).then((T value) {
        handleValue(value, pos);
      }).catchError((error) {
        handleError(error);
      });
      totalScheduled++;
    }

    cycleCount++;
    log.info(
        "Task Group Cycle #$cycleCount: runningTasks=${runningTasks.length}  total scheduled=$totalScheduled  remaining=${tasks.length - totalScheduled}");

    // Wait for RATE_LIMIT_WINDOW if there are any pending tasks to be scheduled,
    // otherwise break the scheduling loop and wait for the task group to finish.
    if (!completer.isCompleted && totalScheduled < tasks.length) {
      log.info(
          "Task Group Cycle #$cycleCount: Rate limiting for 1 second before scheduling next pending tasks.");
      await Future.delayed(const Duration(seconds: 1));
    } else {
      break;
    }
  }

  return completer.future;
}

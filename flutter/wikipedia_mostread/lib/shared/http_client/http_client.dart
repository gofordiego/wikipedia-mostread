import 'dart:io';

import 'package:http/http.dart';
import 'package:http/io_client.dart';

Client httpClient() => IOClient(HttpClient()..userAgent = 'test');

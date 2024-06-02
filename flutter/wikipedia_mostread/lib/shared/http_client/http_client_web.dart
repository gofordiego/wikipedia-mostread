import 'package:http/http.dart';
import 'package:fetch_client/fetch_client.dart';

Client httpClient() => FetchClient(mode: RequestMode.cors);

import 'package:logging/logging.dart';
import 'package:web/web.dart';

import 'wiki_api.dart';

final log = Logger('wiki_cache_web');

WikiCache? wikiCache() => WikiCacheWeb();

class WikiCacheWeb extends WikiCache {
  final _localStorage = window.localStorage;

  @override
  WikiAPIResponse? get(WikiAPIUrl url) {
    try {
      final cachedContent = _localStorage[url.cacheKey];
      if (cachedContent != null) {
        return WikiAPIResponse.fromCache(url, cachedContent);
      }
    } catch (e) {
      log.severe("get error: $e");
    }
    return null;
  }

  @override
  void put(WikiAPIResponse resp) {
    try {
      assert(resp.isValid);
      _localStorage[resp.url.cacheKey] = resp.processedContent;
    } catch (e) {
      log.severe("put error: $e");
    }
  }
}

/// Aligné sur `normalizeVirtualVisualizationInput` / `isVirtualVisualizationEmbedUrl`
/// (`services/arquantix/web/src/lib/vault/normalizeVirtualVisualizationUrl.ts`).
String normalizeVirtualVisualizationInput(String raw) {
  var t = raw.trim();
  if (t.isEmpty) return '';
  var candidate = t;
  if (RegExp(r'<iframe\b', caseSensitive: false).hasMatch(t)) {
    String? extracted;
    final doubleQuote = RegExp(r'src\s*=\s*"([^"]*)"', caseSensitive: false).firstMatch(t);
    if (doubleQuote != null) {
      extracted = doubleQuote.group(1)?.trim();
    }
    extracted ??=
        RegExp(r"src\s*=\s*'([^']*)'", caseSensitive: false).firstMatch(t)?.group(1)?.trim();
    if (extracted != null && extracted.isNotEmpty) {
      candidate = extracted;
    }
  }
  candidate = candidate.trim();
  if (candidate.isEmpty) return '';
  var toParse = candidate;
  if (!RegExp(r'^https?://', caseSensitive: false).hasMatch(toParse)) {
    if (toParse.startsWith('//')) {
      toParse = 'https:$toParse';
    } else if (!toParse.contains('://')) {
      toParse = 'https://$toParse';
    }
  }
  final uri = Uri.tryParse(toParse);
  if (uri == null) return '';
  if (uri.scheme != 'http' && uri.scheme != 'https') return '';
  return uri.toString();
}

bool isVirtualVisualizationEmbedUrl(String url) {
  return url.isNotEmpty && RegExp(r'^https?://', caseSensitive: false).hasMatch(url);
}

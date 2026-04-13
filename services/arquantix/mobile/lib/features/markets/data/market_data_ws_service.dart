import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../core/config.dart';

/// Update de prix reçu via WebSocket (symbol provider, ex. BTCUSDT).
class QuoteUpdate {
  const QuoteUpdate({required this.symbol, required this.price, this.priceEur});

  final String symbol;
  /// Price in USD/USDT.
  final double price;
  /// Price in EUR (if available from backend).
  final double? priceEur;
}

/// Service WebSocket léger pour les quotes market-data.
/// Connexion uniquement pour les symboles demandés ; pas d'auth.
/// En cas d'échec : retry simple puis échec silencieux.
class MarketDataWsService {
  MarketDataWsService() : _baseUrl = Config.wsMarketDataBaseUrl;

  final String _baseUrl;
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  bool _disposeRequested = false;
  int _messageCount = 0;

  static const int _maxRetries = 3;
  static const Duration _retryDelay = Duration(seconds: 2);

  /// Connecte au WS avec les symboles donnés et appelle [onQuotes] à chaque message.
  /// Si déjà connecté avec d'autres symboles, déconnecte d'abord.
  void subscribe(
    List<String> symbols,
    void Function(List<QuoteUpdate> updates) onQuotes,
  ) {
    disconnect();
    if (symbols.isEmpty) return;

    _disposeRequested = false;
    _messageCount = 0;
    final symbolsQuery = symbols.map((s) => s.trim().toUpperCase()).join(',');
    final uri = Uri.parse(Config.wsMarketDataUrl(symbolsQuery));
    if (kDebugMode) print('[MarketDataWS] subscribe: $uri');

    void connectAttempt(int attempt) {
      if (_disposeRequested) return;
      try {
        _channel = WebSocketChannel.connect(uri);
        _subscription = _channel!.stream.listen(
          (data) {
            if (_disposeRequested) return;
            try {
              final json = jsonDecode(data is String ? data : utf8.decode(data as List<int>))
                  as Map<String, dynamic>;
              final raw = json['quotes'];
              if (raw is! List) return;
              final updates = <QuoteUpdate>[];
              for (final e in raw) {
                if (e is! Map<String, dynamic>) continue;
                final symbol = (e['symbol'] ?? '').toString().trim().toUpperCase();
                if (symbol.isEmpty) continue;
                final priceValue = e['price'];
                final price = priceValue is num
                    ? (priceValue).toDouble()
                    : double.tryParse((priceValue ?? '').toString().replaceAll(',', '.'));
                if (price != null && price > 0) {
                  final priceEurVal = e['price_eur'];
                  final priceEur = priceEurVal is num
                      ? priceEurVal.toDouble()
                      : double.tryParse((priceEurVal ?? '').toString());
                  updates.add(QuoteUpdate(symbol: symbol, price: price, priceEur: priceEur));
                }
              }
              if (updates.isNotEmpty) {
                if (kDebugMode) {
                  _messageCount++;
                  final showDetail = _messageCount == 1 || _messageCount % 10 == 0;
                  print('[MarketDataWS] message #$_messageCount: ${updates.length} quotes'
                      '${showDetail ? " → ${updates.map((u) => "${u.symbol}: ${u.price}").join(", ")}" : ""}');
                }
                onQuotes(updates);
              }
            } catch (_) {
              // ignore parse errors
            }
          },
          onError: (Object e, StackTrace? st) {
            if (_disposeRequested) return;
            if (kDebugMode) print('[MarketDataWS] onError: $e');
            _channel = null;
            _subscription?.cancel();
            _subscription = null;
            if (attempt < _maxRetries) {
              Future.delayed(_retryDelay, () => connectAttempt(attempt + 1));
            }
          },
          onDone: () {
            _channel = null;
            _subscription = null;
            if (_disposeRequested) return;
            if (kDebugMode) print('[MarketDataWS] onDone (attempt $attempt)');
            if (attempt < _maxRetries) {
              Future.delayed(_retryDelay, () => connectAttempt(attempt + 1));
            }
          },
          cancelOnError: false,
        );
      } catch (_) {
        if (_disposeRequested) return;
        if (attempt < _maxRetries) {
          Future.delayed(_retryDelay, () => connectAttempt(attempt + 1));
        }
      }
    }

    connectAttempt(0);
  }

  /// Déconnecte et annule les retries.
  void disconnect() {
    _disposeRequested = true;
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
  }
}

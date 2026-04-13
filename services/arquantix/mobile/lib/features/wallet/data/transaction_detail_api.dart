import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/transaction_detail.dart';

class TransactionDetailApiException implements Exception {
  final String message;
  final int? statusCode;

  TransactionDetailApiException(this.message, {this.statusCode});

  @override
  String toString() => 'TransactionDetailApiException($statusCode): $message';
}

class TransactionDetailApi {
  const TransactionDetailApi();

  Future<TransactionDetail> fetchDetail(String transactionId) async {
    final url = Uri.parse(Config.transactionDetailUrl(transactionId));
    final response = await http.get(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'TransactionDetailApi.fetchDetail',
      ),
    );

    if (response.statusCode == 404) {
      throw TransactionDetailApiException(
        'Transaction not found',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw TransactionDetailApiException(
        'Failed to fetch transaction detail',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return TransactionDetail.fromJson(json);
  }
}

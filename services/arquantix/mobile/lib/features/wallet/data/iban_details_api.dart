import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/iban_details.dart';

class IbanDetailsApi {
  Future<IbanDetails?> fetchIbanDetails() async {
    final uri = Uri.parse(Config.ibanDetailsUrl);
    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'IbanDetailsApi.fetchIbanDetails',
      ),
    );

    if (response.statusCode == 404) return null;

    if (response.statusCode != 200) {
      throw Exception('IbanDetailsApi error ${response.statusCode}');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final details = json['iban_details'] as Map<String, dynamic>?;
    if (details == null) return null;
    return IbanDetails.fromJson(details);
  }
}

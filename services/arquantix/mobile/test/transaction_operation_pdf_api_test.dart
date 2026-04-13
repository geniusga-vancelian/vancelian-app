import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/wallet/data/transaction_operation_pdf_api.dart';

void main() {
  group('parseOperationStatementErrorBody', () {
    test('FastAPI detail string', () {
      expect(
        parseOperationStatementErrorBody('{"detail":"Relevé indisponible."}'),
        'Relevé indisponible.',
      );
    });

    test('Next BFF message without detail', () {
      expect(
        parseOperationStatementErrorBody(
          '{"error":"Internal server error","message":"The request could not be completed."}',
        ),
        'The request could not be completed.',
      );
    });

    test('empty body', () {
      expect(parseOperationStatementErrorBody(''), isNull);
    });
  });
}

import 'package:arquantix_news/features/security/login/presentation/login_email_fallback_screen.dart';
import 'package:arquantix_news/features/security/passcode/domain/passcode_storage_keys.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'LoginEmailFallbackScreen : champ e-mail vide même si login_last_email est en stockage',
    (tester) async {
      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.loginLastEmail: 'stale@example.com',
      });
      await tester.pumpWidget(
        const MaterialApp(
          home: LoginEmailFallbackScreen(),
        ),
      );
      await tester.pumpAndSettle();

      final editable = find.byType(EditableText);
      expect(editable, findsWidgets);
      expect(
        tester.widget<EditableText>(editable.first).controller.text,
        '',
      );
      expect(find.text('stale@example.com'), findsNothing);
    },
  );
}

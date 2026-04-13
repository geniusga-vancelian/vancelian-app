import 'package:flutter/material.dart';

import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../application/passkey_service.dart';
import '../data/passkey_api.dart';
import '../data/passkey_platform_provider_factory.dart';
import '../domain/passkey_exceptions.dart';

/// Enrôlement passkey depuis un compte déjà authentifié (réglages sécurité).
class PasskeySetupScreen extends StatefulWidget {
  const PasskeySetupScreen({super.key});

  @override
  State<PasskeySetupScreen> createState() => _PasskeySetupScreenState();
}

class _PasskeySetupScreenState extends State<PasskeySetupScreen> {
  bool _busy = false;
  String? _message;

  Future<void> _addPasskey() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    final token = await SessionService.instance.readAccessToken();
    if (token == null || token.isEmpty) {
      setState(() {
        _busy = false;
        _message = 'Session requise.';
      });
      return;
    }
    final api = PasskeyApi();
    final service = PasskeyService(
      api: api,
      provider: createPasskeyProvider(),
      getDeviceId: () => DeviceIdService.instance.getOrCreate(),
      getFingerprintHeader: () => DeviceIdService.instance.buildFingerprintHeaderJson(),
    );
    await api.reportPrompt(event: 'auth.passkey.prompt.opened');
    try {
      await service.enrollPasskey(accessToken: token, deviceLabel: 'Mobile');
      setState(() {
        _busy = false;
        _message = 'Passkey enregistrée.';
      });
    } on PasskeyUserCancelledException catch (_) {
      await api.reportPrompt(event: 'auth.passkey.prompt.cancelled');
      setState(() {
        _busy = false;
        _message = 'Enregistrement annulé.';
      });
    } on PasskeyUnavailableException catch (_) {
      await api.reportPrompt(event: 'auth.passkey.prompt.failed', detail: 'unavailable');
      setState(() {
        _busy = false;
        _message =
            'Passkeys non disponibles sur cet appareil. Utilisez OTP ou mot de passe.';
      });
    } on PasskeyAuthenticatorFailureException catch (e) {
      await api.reportPrompt(event: 'auth.passkey.prompt.failed', detail: e.message);
      setState(() {
        _busy = false;
        _message = 'Échec de l’enregistrement. Réessayez ou utilisez OTP.';
      });
    } on PasskeyApiException catch (e) {
      setState(() {
        _busy = false;
        _message = 'Erreur serveur (${e.statusCode}).';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ajouter une passkey')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Associez une passkey à votre compte. Un flux natif (Face ID, Touch ID ou '
              'sécurité équivalente Android) s’ouvre sur l’appareil.',
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _addPasskey,
              child: Text(_busy ? 'Patientez…' : 'Add Passkey'),
            ),
            if (_message != null) ...[
              const SizedBox(height: 16),
              Text(_message!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ],
        ),
      ),
    );
  }
}

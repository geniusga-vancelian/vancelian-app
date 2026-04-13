import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../data/passkey_api.dart';
import '../domain/passkey_exceptions.dart';

/// Connexion admin par code e-mail (API auth), alignée sur les sessions passkey / mot de passe.
class AdminEmailOtpLoginScreen extends StatefulWidget {
  const AdminEmailOtpLoginScreen({super.key, required this.email});

  final String email;

  @override
  State<AdminEmailOtpLoginScreen> createState() => _AdminEmailOtpLoginScreenState();
}

class _AdminEmailOtpLoginScreenState extends State<AdminEmailOtpLoginScreen> {
  final _api = PasskeyApi();
  final _codeCtrl = TextEditingController();
  bool _sending = false;
  bool _verifying = false;
  String? _message;

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _sendCode() async {
    setState(() {
      _sending = true;
      _message = null;
    });
    try {
      final body = await _api.adminEmailOtpStart(email: widget.email);
      final dc = body['dev_code'];
      final devHint = dc is String && dc.length == 6
          ? ' Mode test : utilisez $dc.'
          : '';
      setState(() {
        _sending = false;
        _message =
            'Si un compte existe pour cet e-mail, un code vient d’être envoyé.$devHint';
      });
    } on PasskeyApiException catch (e) {
      setState(() {
        _sending = false;
        if (e.statusCode == 503) {
          _message =
              'Connexion par code désactivée ou e-mail non configuré sur le serveur. Utilisez une passkey ou le mot de passe.';
        } else {
          _message = 'Envoi impossible (${e.statusCode}). Réessayez plus tard.';
        }
      });
    }
  }

  Future<void> _verify() async {
    final code = _codeCtrl.text.trim();
    if (code.length < 6) {
      setState(() => _message = 'Saisissez le code à 6 chiffres.');
      return;
    }
    SessionStateMachine.instance.apply(SessionLifecycleEvent.loginFlowStarted);
    setState(() {
      _verifying = true;
      _message = null;
    });
    try {
      final deviceId = await DeviceIdService.instance.getOrCreate();
      final fp = await DeviceIdService.instance.buildFingerprintHeaderJson();
      final tokens = await _api.adminEmailOtpVerify(
        email: widget.email,
        code: code,
        deviceId: deviceId,
        fingerprintHeader: fp,
      );
      final at = tokens['access_token'] as String?;
      final rt = tokens['refresh_token'] as String?;
      if (at == null || at.isEmpty) {
        setState(() {
          _verifying = false;
          _message = 'Réponse serveur inattendue.';
        });
        return;
      }
      await SessionService.instance.storeTokens(accessToken: at, refreshToken: rt);
      if (!mounted) return;
      setState(() => _verifying = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Connecté')));
      Navigator.of(context).pop(true);
    } on PasskeyApiException catch (e) {
      setState(() {
        _verifying = false;
        _message = e.statusCode == 401 ? 'Code incorrect ou expiré.' : 'Vérification impossible (${e.statusCode}).';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Code par e-mail')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'E-mail : ${widget.email}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: AppSpacing.lg),
            FilledButton(
              onPressed: _sending ? null : _sendCode,
              child: Text(_sending ? 'Envoi…' : 'Envoyer le code'),
            ),
            const SizedBox(height: AppSpacing.xl),
            TextField(
              controller: _codeCtrl,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(8)],
              decoration: const InputDecoration(
                labelText: 'Code reçu',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            FilledButton(
              onPressed: _verifying ? null : _verify,
              child: Text(_verifying ? 'Vérification…' : 'Se connecter'),
            ),
            if (_message != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(_message!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ],
        ),
      ),
    );
  }
}
